"""
Adaptador de salida - Repositorio de películas con Filesystem
Implementación de IMovieRepository con sistema de caché eficiente
"""
import os
import re
import time
import json
import hashlib
import logging
import threading
from typing import List, Optional, Dict, Union
from src.core.ports.repositories.movie_repository import IMovieRepository


# Configurar logger
logger = logging.getLogger(__name__)


class FilesystemMovieRepository(IMovieRepository):
    """Repositorio de películas escaneando el sistema de archivos con caché"""
    
    def __init__(self, base_folder: str = None, ttl_seconds: int = 300):
        """
        Inicializa el repositorio con caché
        
        Args:
            base_folder: Carpeta base donde están las películas
            ttl_seconds: Tiempo de vida de la caché en segundos (default: 300 = 5 minutos)
        """
        self._base_folder = base_folder or os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
        self._valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
        
        # Configuración de caché
        self._cache = {}
        self._movie_index = {}  # Índice O(1) por ID
        self._cache_timestamp = None
        # TTL configurable via variable de entorno o parámetro
        env_ttl = os.environ.get('MOVIE_CACHE_TTL_SECONDS')
        self._ttl_seconds = int(env_ttl) if env_ttl else ttl_seconds
        self._lock = threading.RLock()  # Thread-safe
        
        # Archivo de índice persistente
        self._index_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            '.movie_index_cache.json'
        )
        
        # Intentar cargar índice persistente al iniciar
        self._load_persistent_index()
        
        logger.info(f"FilesystemMovieRepository inicializado con TTL={ttl_seconds}s, base_folder={self._base_folder}")
    
    def _generate_movie_id(self, file_path: str) -> str:
        """
        Genera un ID estable basado en el hash MD5 del path
        
        Args:
            file_path: Ruta absoluta del archivo
            
        Returns:
            ID con formato: mov_{hash_md5[:8]}
        """
        hash_md5 = hashlib.md5(file_path.encode('utf-8')).hexdigest()
        return f"mov_{hash_md5[:8]}"
    
    def _ensure_cache(self) -> bool:
        """
        Verifica si la caché necesita refrescarse
        
        Returns:
            True si se refrescó la caché, False si se usó la caché existente
        """
        with self._lock:
            current_time = time.time()
            
            # Verificar si la caché necesita refrescarse
            if (self._cache_timestamp is None or 
                current_time - self._cache_timestamp > self._ttl_seconds):
                
                logger.info("Refrescando caché de películas...")
                scan_start = time.time()
                
                # Escanear el directorio
                movies = self._scan_folder()
                
                # Construir índice
                self._movie_index = {}
                for movie in movies:
                    movie_id = movie['id']
                    self._movie_index[movie_id] = movie
                
                # Actualizar caché
                self._cache = {'movies': movies, 'count': len(movies)}
                self._cache_timestamp = current_time
                
                scan_duration = time.time() - scan_start
                logger.info(f"Caché refrescada: {len(movies)} películas escaneadas en {scan_duration:.2f}s")
                
                # Guardar índice persistente
                self._save_persistent_index()
                
                return True
            
            return False
    
    def _load_persistent_index(self):
        """Carga el índice persistente desde archivo JSON si existe"""
        try:
            if os.path.exists(self._index_file):
                with open(self._index_file, 'r') as f:
                    data = json.load(f)
                    self._cache = data.get('cache', {})
                    self._movie_index = data.get('index', {})
                    self._cache_timestamp = data.get('timestamp')
                    logger.info(f"Índice persistente cargado: {len(self._movie_index)} películas")
        except Exception as e:
            logger.warning(f"No se pudo cargar índice persistente: {e}")
    
    def _save_persistent_index(self):
        """Guarda el índice en archivo JSON para persistencia"""
        try:
            data = {
                'cache': self._cache,
                'index': self._movie_index,
                'timestamp': self._cache_timestamp
            }
            with open(self._index_file, 'w') as f:
                json.dump(data, f)
            logger.debug("Índice persistente guardado")
        except Exception as e:
            logger.warning(f"No se pudo guardar índice persistente: {e}")
    
    def _parse_filename(self, filename: str) -> tuple:
        """
        Parsea el nombre del archivo para extraer título y año
        Soporta múltiples formatos:
        - nombre-(año).ext
        - nombre-(año)-optimized.ext
        - nombre.año.ext
        - nombre (año).ext
        - nombre-año.ext
        """
        # Quitar extensión
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Quitar sufijos comunes
        name_clean = name_without_ext
        for suffix in ['-optimized', '-HD', '-4K', '-BluRay', '-WEB', '-DL', '-AC3']:
            name_clean = name_clean.replace(suffix, '')
        
        # Buscar año en diferentes formatos
        year = None
        
        # Formato: (2024)
        year_match = re.search(r'\((\d{4})\)', name_clean)
        if year_match:
            year = int(year_match.group(1))
            name_clean = re.sub(r'\(\d{4}\)', '', name_clean)
        
        # Formato: .2024. o -2024- o _2024_
        if year is None:
            year_match = re.search(r'[.\-_ ](\d{4})[.\-_ ]', name_clean)
            if year_match:
                year = int(year_match.group(1))
                name_clean = name_clean.replace(year_match.group(0), ' ')
        
        # Formato: nombre.2024 al final
        if year is None:
            year_match = re.search(r'(\d{4})$', name_clean.strip())
            if year_match:
                year = int(year_match.group(1))
                name_clean = name_clean[:-4].strip()
        
        # Limpiar el título
        title = name_clean.replace('-', ' ').replace('_', ' ').strip()
        title = re.sub(r'\s+', ' ', title)  # Múltiples espacios a uno solo
        
        return title, year
    
    def _scan_folder(self) -> List[Dict]:
        """Escanea la carpeta de películas de forma optimizada"""
        movies = []
        
        if not os.path.exists(self._base_folder):
            logger.warning(f"La carpeta base no existe: {self._base_folder}")
            return movies
        
        # Buscar en subcarpeta mkv primero
        mkv_folder = os.path.join(self._base_folder, 'mkv')
        if os.path.exists(mkv_folder):
            scan_folder = mkv_folder
        else:
            scan_folder = self._base_folder
        
        logger.debug(f"Escaneando carpeta: {scan_folder}")
        
        # Usar os.scandir en lugar de os.walk para mejor rendimiento
        try:
            entries = list(os.scandir(scan_folder))
        except PermissionError:
            logger.error(f"Permission denied: {scan_folder}")
            return movies
        
        # Recorrer solo directorios de nivel superior (más eficiente)
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                self._scan_directory(entry.path, movies)
            elif entry.is_file(follow_symlinks=False):
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in self._valid_extensions:
                    movie = self._create_movie_entry(entry.path, entry.name)
                    if movie:
                        movies.append(movie)
        
        return movies
    
    def _scan_directory(self, dir_path: str, movies: List[Dict]):
        """Escanea un directorio de forma recursiva"""
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        self._scan_directory(entry.path, movies)
                    elif entry.is_file(follow_symlinks=False):
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in self._valid_extensions:
                            movie = self._create_movie_entry(entry.path, entry.name)
                            if movie:
                                movies.append(movie)
        except PermissionError:
            logger.warning(f"Permission denied: {dir_path}")
    
    def _create_movie_entry(self, file_path: str, filename: str) -> Optional[Dict]:
        """Crea una entrada de película con metadatos"""
        try:
            # Parsear título y año
            title, year = self._parse_filename(filename)
            
            # Obtener tamaño
            size = os.path.getsize(file_path)
            
            # Calcular si es una película nueva (modificada en los últimos 30 días)
            try:
                mtime = os.path.getmtime(file_path)
                days_ago = int((time.time() - mtime) / (24 * 3600))
                is_new = days_ago <= 30
            except:
                days_ago = -1
                is_new = False
            
            # Generar ID estable basado en hash del path
            movie_id = self._generate_movie_id(file_path)
            
            movie = {
                'id': movie_id,
                'filename': filename,
                'title': title,
                'year': year,
                'path': file_path,
                'size': size,
                'is_optimized': '-optimized' in filename,
                'ext': os.path.splitext(filename)[1].lower(),
                'is_new': is_new,
                'days_ago': days_ago
            }
            
            return movie
        except Exception as e:
            logger.warning(f"Error al crear entrada para {file_path}: {e}")
            return None
    
    def _get_movies_from_cache(self) -> List[Dict]:
        """Obtiene las películas de la caché, refrescándola si es necesario"""
        self._ensure_cache()
        return self._cache.get('movies', [])
    
    def list_all(self) -> List[Dict]:
        """Lista todas las películas"""
        start_time = time.time()
        movies = self._get_movies_from_cache()
        duration = time.time() - start_time
        logger.info(f"list_all(): {len(movies)} películas devueltas en {duration:.4f}s")
        return movies
    
    def get_by_id(self, movie_id: Union[int, str]) -> Optional[Dict]:
        """
        Obtiene una película por su ID
        
        Args:
            movie_id: ID de la película (puede ser string con formato 'mov_xxxx' o int para compatibilidad hacia atrás)
            
        Returns:
            Diccionario con los datos de la película o None si no existe
        """
        start_time = time.time()
        
        # Asegurar caché actualizada
        self._ensure_cache()
        
        # Manejar compatibilidad hacia atrás con IDs enteros
        if isinstance(movie_id, int):
            # Para IDs enteros, usar índice por posición (compatibilidad)
            movies = self._cache.get('movies', [])
            if 0 <= movie_id < len(movies):
                movie = movies[movie_id]
                duration = time.time() - start_time
                logger.info(f"get_by_id({movie_id}): película '{movie.get('title')}' encontrada en {duration:.4f}s (índice)")
                return movie
            duration = time.time() - start_time
            logger.info(f"get_by_id({movie_id}): no encontrada en {duration:.4f}s")
            return None
        
        # Búsqueda O(1) por ID string
        movie = self._movie_index.get(str(movie_id))
        duration = time.time() - start_time
        
        if movie:
            logger.info(f"get_by_id('{movie_id}'): película '{movie.get('title')}' encontrada en {duration:.4f}s (hash index)")
        else:
            logger.info(f"get_by_id('{movie_id}'): no encontrada en {duration:.4f}s")
        
        return movie
    
    def get_by_path(self, path: str) -> Optional[Dict]:
        """Obtiene una película por su ruta"""
        start_time = time.time()
        
        self._ensure_cache()
        
        # Buscar en el índice por path
        for movie in self._movie_index.values():
            if movie.get('path') == path:
                duration = time.time() - start_time
                logger.info(f"get_by_path('{path}'): encontrada en {duration:.4f}s")
                return movie
        
        duration = time.time() - start_time
        logger.info(f"get_by_path('{path}'): no encontrada en {duration:.4f}s")
        return None
    
    def get_by_filename(self, filename: str) -> Optional[Dict]:
        """Obtiene una película por su nombre de archivo"""
        start_time = time.time()
        
        self._ensure_cache()
        
        # Buscar en caché
        for movie in self._movie_index.values():
            if movie.get('filename') == filename:
                duration = time.time() - start_time
                logger.info(f"get_by_filename('{filename}'): encontrada en {duration:.4f}s")
                return movie
        
        duration = time.time() - start_time
        logger.info(f"get_by_filename('{filename}'): no encontrada en {duration:.4f}s")
        return None
    
    def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Obtiene una película por su ID de IMDb"""
        # No disponible en filesystem sin metadatos externos
        return None
    
    def search(self, query: str) -> List[Dict]:
        """Busca películas por título"""
        start_time = time.time()
        
        movies = self._get_movies_from_cache()
        query_lower = query.lower()
        
        results = [
            m for m in movies
            if query_lower in m.get('title', '').lower()
        ]
        
        duration = time.time() - start_time
        logger.info(f"search('{query}'): {len(results)} resultados en {duration:.4f}s")
        
        return results
    
    def get_by_genre(self, genre: str) -> List[Dict]:
        """Obtiene películas por género"""
        # No disponible sin metadatos
        return []
    
    def get_by_year(self, year: int) -> List[Dict]:
        """Obtiene películas por año"""
        start_time = time.time()
        
        movies = self._get_movies_from_cache()
        results = [m for m in movies if m.get('year') == year]
        
        duration = time.time() - start_time
        logger.info(f"get_by_year({year}): {len(results)} resultados en {duration:.4f}s")
        
        return results
    
    def get_optimized(self) -> List[Dict]:
        """Obtiene solo películas optimizadas"""
        start_time = time.time()
        
        movies = self._get_movies_from_cache()
        results = [m for m in movies if m.get('is_optimized')]
        
        duration = time.time() - start_time
        logger.info(f"get_optimized(): {len(results)} resultados en {duration:.4f}s")
        
        return results
    
    def save(self, movie_data: Dict) -> Dict:
        """Guarda o actualiza una película"""
        # No aplicable en filesystem
        return movie_data
    
    def delete(self, movie_id: Union[int, str]) -> bool:
        """Elimina una película"""
        # No soportado en este repositorio
        return False
    
    def update_metadata(self, movie_id: Union[int, str], metadata: Dict) -> Dict:
        """Actualiza los metadatos de la película"""
        # No aplicable en filesystem
        return metadata
    
    def get_random(self, limit: int = 10) -> List[Dict]:
        """Obtiene películas aleatorias"""
        import random
        
        start_time = time.time()
        movies = self._get_movies_from_cache()
        
        if len(movies) <= limit:
            results = movies[:]
        else:
            results = random.sample(movies, limit)
        
        duration = time.time() - start_time
        logger.info(f"get_random({limit}): {len(results)} resultados en {duration:.4f}s")
        
        return results
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Obtiene las películas más recientes (por fecha de modificación)"""
        start_time = time.time()
        
        movies = self._get_movies_from_cache()
        
        # Ordenar por fecha de modificación (más reciente primero)
        try:
            movies.sort(key=lambda m: os.path.getmtime(m['path']), reverse=True)
        except OSError:
            pass  # Si falla, devolver sin ordenar
        
        results = movies[:limit]
        
        duration = time.time() - start_time
        logger.info(f"get_recent({limit}): {len(results)} resultados en {duration:.4f}s")
        
        return results
    
    def invalidate_cache(self):
        """Fuerza la invalidación de la caché"""
        with self._lock:
            self._cache_timestamp = None
            self._cache = {}
            self._movie_index = {}
            logger.info("Caché invalidada manualmente")
    
    def get_cache_stats(self) -> Dict:
        """Obtiene estadísticas de la caché"""
        return {
            'ttl_seconds': self._ttl_seconds,
            'cached_movies': len(self._movie_index),
            'cache_age_seconds': time.time() - self._cache_timestamp if self._cache_timestamp else None,
            'index_file': self._index_file
        }
