"""
Adaptador de salida - Repositorio de películas con Filesystem
Implementación de IMovieRepository escaneando archivos del disco
"""
import os
import re
import time
from typing import List, Optional, Dict
from src.core.ports.repositories.movie_repository import IMovieRepository


class FilesystemMovieRepository(IMovieRepository):
    """Repositorio de películas escaneando el sistema de archivos"""
    
    def __init__(self, base_folder: str = None):
        """
        Inicializa el repositorio
        
        Args:
            base_folder: Carpeta base donde están las películas
        """
        self._base_folder = base_folder or os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
        self._valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
        self._cache = {}  # Cache en memoria
    
    def _parse_filename(self, filename: str) -> tuple:
        """
        Parsea el nombre del archivo para extraer título y año
        Formato esperado: nombre-(año).ext o nombre-(año)-optimized.ext
        """
        # Quitar extensión
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Quitar sufijo -optimized si existe
        name_without_suffix = name_without_ext.replace('-optimized', '')
        
        # Buscar año entre paréntesis
        year_match = re.search(r'\((\d{4})\)', name_without_suffix)
        year = int(year_match.group(1)) if year_match else None
        
        # Quitar el año del título
        if year:
            title = re.sub(r'\(\d{4}\)', '', name_without_suffix).strip('-').strip()
        else:
            title = name_without_suffix
        
        # Limpiar el título
        title = title.replace('-', ' ').strip()
        
        return title, year
    
    def _scan_folder(self) -> List[Dict]:
        """Escanea la carpeta de películas"""
        movies = []
        
        if not os.path.exists(self._base_folder):
            return movies
        
        # Buscar en subcarpeta mkv
        mkv_folder = os.path.join(self._base_folder, 'mkv')
        if os.path.exists(mkv_folder):
            scan_folder = mkv_folder
        else:
            scan_folder = self._base_folder
        
        for root, _, files in os.walk(scan_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self._valid_extensions:
                    file_path = os.path.join(root, file)
                    
                    # Parsear título y año
                    title, year = self._parse_filename(file)
                    
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
                    
                    movie = {
                        'filename': file,
                        'title': title,
                        'year': year,
                        'path': file_path,
                        'size': size,
                        'is_optimized': '-optimized' in file,
                        'ext': ext,
                        'is_new': is_new,
                        'days_ago': days_ago
                    }
                    
                    movies.append(movie)
        
        return movies
    
    def list_all(self) -> List[Dict]:
        """Lista todas las películas"""
        return self._scan_folder()
    
    def get_by_id(self, movie_id: int) -> Optional[Dict]:
        """Obtiene una película por su ID"""
        # En filesystem no hay IDs, buscar por índice
        movies = self._scan_folder()
        if 0 <= movie_id < len(movies):
            return movies[movie_id]
        return None
    
    def get_by_path(self, path: str) -> Optional[Dict]:
        """Obtiene una película por su ruta"""
        movies = self._scan_folder()
        for movie in movies:
            if movie['path'] == path:
                return movie
        return None
    
    def get_by_filename(self, filename: str) -> Optional[Dict]:
        """Obtiene una película por su nombre de archivo"""
        movies = self._scan_folder()
        for movie in movies:
            if movie['filename'] == filename:
                return movie
        return None
    
    def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Obtiene una película por su ID de IMDb"""
        # No disponible en filesystem
        return None
    
    def search(self, query: str) -> List[Dict]:
        """Busca películas por título"""
        movies = self._scan_folder()
        query_lower = query.lower()
        
        return [
            m for m in movies
            if query_lower in m['title'].lower()
        ]
    
    def get_by_genre(self, genre: str) -> List[Dict]:
        """Obtiene películas por género"""
        # No disponible sin metadatos
        return []
    
    def get_by_year(self, year: int) -> List[Dict]:
        """Obtiene películas por año"""
        movies = self._scan_folder()
        return [m for m in movies if m.get('year') == year]
    
    def get_optimized(self) -> List[Dict]:
        """Obtiene solo películas optimizadas"""
        movies = self._scan_folder()
        return [m for m in movies if m.get('is_optimized')]
    
    def save(self, movie_data: Dict) -> Dict:
        """Guarda o actualiza una película"""
        # No aplicable en filesystem
        return movie_data
    
    def delete(self, movie_id: int) -> bool:
        """Elimina una película"""
        # No soportado en este repositorio
        return False
    
    def update_metadata(self, movie_id: int, metadata: Dict) -> Dict:
        """Actualiza los metadatos de una película"""
        # No aplicable en filesystem
        return metadata
    
    def get_random(self, limit: int = 10) -> List[Dict]:
        """Obtiene películas aleatorias"""
        import random
        movies = self._scan_folder()
        return random.sample(movies, min(len(movies), limit))
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Obtiene las películas más recientes (por fecha de modificación)"""
        movies = self._scan_folder()
        # Ordenar por fecha de modificación (más reciente primero)
        movies.sort(key=lambda m: os.path.getmtime(m['path']), reverse=True)
        return movies[:limit]
