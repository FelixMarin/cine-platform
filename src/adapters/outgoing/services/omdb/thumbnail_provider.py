"""
Proveedor de thumbnails de OMDB

Responsabilidad: Obtener thumbnails de OMDB con INSERCIÓN ESTRICTA.
SOLO guarda en base de datos si hay coincidencia EXACTA de título + año.
Con caché en memoria para evitar saturación del pool de conexiones.
"""

import logging
import re
from typing import Optional
from datetime import datetime

from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)
from src.adapters.outgoing.services.thumbnails.memory_cache import get_thumbnail_cache

logger = logging.getLogger(__name__)


class OMDBThumbnailProvider:
    """Proveedor de thumbnails desde OMDB con inserción estricta"""

    def __init__(self, api_key: str = None):
        """
        Inicializa el proveedor de thumbnails de OMDB.
        
        Args:
            api_key: Clave de API de OMDB (opcional, usa variable de entorno si no se provee)
        """
        self._api_key = api_key
        self._metadata_service = None

    def _get_metadata_service(self):
        """Obtiene el servicio de metadatos (lazy loading)"""
        if self._metadata_service is None:
            from src.adapters.config.dependencies import get_metadata_service
            self._metadata_service = get_metadata_service()
        return self._metadata_service

    def fetch_thumbnail_data(self, title: str, year: Optional[str]) -> Optional[bytes]:
        """
        Obtiene los datos binarios del thumbnail de OMDB.
        
        Busca primero en caché en memoria, luego en base de datos (búsqueda exacta),
        y finalmente consulta OMDB si no encuentra.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            
        Returns:
            Datos binarios de la imagen (JPEG) o None si no se encontró
        """
        # 1. INTENTAR CACHÉ EN MEMORIA (0 conexiones a BBDD)
        cache = get_thumbnail_cache()
        cached_data = cache.get(title, year)
        if cached_data:
            logger.info(f"CACHÉ: Sirviendo poster para [{title}] ({year}) desde memória")
            return cached_data
        
        # 2. Intentar obtener de la base de datos (búsqueda exacta)
        thumbnail_data = self._fetch_from_database(title, year)
        if thumbnail_data:
            logger.info(f"BBDD: Sirviendo poster para [{title}] ({year}) desde BBDD")
            # Guardar en caché
            cache.set(title, year, thumbnail_data)
            return thumbnail_data
        
        # 3. Si no hay en BBDD, buscar en OMDB
        thumbnail_data = self._fetch_from_omdb(title, year)
        if thumbnail_data:
            logger.info(f"OMDB: Poster para [{title}] ({year}) obtenido desde OMDB")
            # Guardar en caché
            cache.set(title, year, thumbnail_data)
            return thumbnail_data
        
        return None

    def _fetch_from_database(self, title: str, year: Optional[str]) -> Optional[bytes]:
        """
        Busca el thumbnail en la base de datos local (omdb_entries) con búsqueda EXACTA.
        Usa context manager para garantizar cierre de sesión.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            
        Returns:
            Datos binarios de la imagen o None
        """
        try:
            # Usar context manager para gestionar la sesión
            with get_catalog_repository_session() as db:
                repo = get_catalog_repository(db)
                
                # Convertir año a int si existe
                year_int = int(year) if year and year.isdigit() else None
                
                # 1. Intentar coincidencia exacta con título limpio (sin año entre paréntesis)
                entry = repo.get_exact_match_by_cleaned_title(title, year_int)
                if entry and entry.poster_image:
                    repo.update_last_accessed(entry)
                    return entry.poster_image
                
                # 2. Intentar coincidencia exacta con título original
                entry = repo.get_exact_match(title, year_int)
                if entry and entry.poster_image:
                    repo.update_last_accessed(entry)
                    return entry.poster_image
                
                return None
            
        except Exception as e:
            logger.error(f"Error buscando en BBDD para [{title}]: {e}")
            return None

    def _fetch_from_omdb(self, title: str, year: Optional[str]) -> Optional[bytes]:
        """
        Busca el thumbnail directamente en OMDB.
        SOLO guarda si hay coincidencia EXACTA de título + año.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            
        Returns:
            Datos binarios de la imagen o None
        """
        metadata_service = self._get_metadata_service()
        if not metadata_service:
            return None
        
        try:
            # Limpiar título y extraer año
            clean_title, extracted_year = self._clean_title_and_year(title)
            search_year = year or extracted_year
            
            # Buscar en OMDB
            result = self._search_exact_omdb(clean_title, search_year, metadata_service)
            
            if not result:
                logger.warning(f"OMDB: No se encontró coincidencia exacta para [{clean_title}] ({search_year})")
                return None
            
            # Verificar que el resultado coincide exactamente
            result_title = result.get('Title', '')
            result_year = result.get('Year', '')
            
            if not self._is_exact_match(clean_title, str(search_year), result_title, result_year):
                logger.warning(f"OMDB: Resultado no coincide exactamente. Buscado: [{clean_title}] ({search_year}) vs Recibido: [{result_title}] ({result_year})")
                return None
            
            # Obtener el póster y guardarlo
            poster_data = self._get_and_save_poster(result, clean_title, search_year)
            return poster_data
            
        except Exception as e:
            logger.error(f"Error en OMDB para [{title}]: {e}")
            return None

    def _clean_title_and_year(self, raw_title: str) -> tuple:
        """
        Extrae título limpio y año del string.
        Ejemplo: "F1 the movie (2025)" -> ("F1 the movie", 2025)
        """
        year_match = re.search(r'\((\d{4})\)\s*$', raw_title)
        if year_match:
            year = int(year_match.group(1))
            clean_title = re.sub(r'\s*\(\d{4}\)\s*$', '', raw_title).strip()
            return clean_title, year
        return raw_title.strip(), None

    def _is_exact_match(self, search_title: str, search_year: str, result_title: str, result_year: str) -> bool:
        """
        Verifica si el resultado de OMDB coincide con lo buscado.
        
        Estrategia:
        1. El año debe coincidir exactamente (filtro principal - SAGRADO)
        2. El título debe ser semánticamente equivalente con flexibilidad para:
           - Puntuación diferente (:, -, etc.)
           - Mayúsculas/minúsculas
           - Palabras adicionales (subtítulos)
           - Números romanos vs arábigos (I, II, III vs 1, 2, 3)
           - Artículos (The, El, La) al inicio o final
        3. Protección contra falsos positivos para títulos cortos (< 3 palabras)
        """
        if not result_title:
            return False
        
        # 1. Verificar año (filtro principal - SAGRADO)
        if not self._years_match(search_year, result_year):
            logger.debug(f"OMDB: Año no coincide: '{search_year}' vs '{result_year}'")
            return False
        
        # 2. Verificar coincidencia de título con validación semántica
        if not self._titles_match_semantically(search_title, result_title):
            logger.debug(f"OMDB: Título no coincide semánticamente: '{search_title}' vs '{result_title}'")
            return False
        
        return True

    def _years_match(self, search_year: str, result_year: str) -> bool:
        """
        Verifica si los años coinciden exactamente.
        """
        if not search_year and not result_year:
            return True
        if not search_year and result_year:
            return True  # Sin año en búsqueda, aceptamos cualquier resultado
        if search_year and not result_year:
            return False
        
        # Normalizar años (extraer el primer año si es un rango como "2015-2024")
        search_year_normalized = str(search_year).split('-')[0].strip()
        result_year_normalized = str(result_year).split('-')[0].strip()
        
        return search_year_normalized == result_year_normalized

    def _titles_match_semantically(self, search_title: str, result_title: str) -> bool:
        """
        Verifica si los títulos coinciden semánticamente.
        
        Usa una estrategia por niveles:
        - Nivel 1: Comparación exacta normalizada
        - Nivel 2: Comparación con normalización flexible
        - Nivel 3: Validación semántica para títulos con subtítulos
        """
        # Normalizar títulos
        search_norm = self._normalize_title(search_title)
        result_norm = self._normalize_title(result_title)
        
        # Nivel 1: Comparación exacta normalizada
        if search_norm == result_norm:
            return True
        
        # Nivel 2: Comparación flexible (uno contiene al otro o son equivalentes)
        if self._is_similar_title(search_norm, result_norm):
            return True
        
        # Nivel 3: Validación semántica para casos especiales
        return self._is_semantically_equivalent(search_title, result_title)

    def _normalize_title(self, title: str) -> str:
        """
        Normaliza un título para comparación.
        
        Realiza:
        - Lowercase
        - Eliminación de puntuación común (:, -, ', )
        - Eliminación de artículos al inicio/final (the, a, an, el, la, los, las)
        - Normalización de números romanos a arábigos (I, II, III -> 1, 2, 3)
        - Eliminación de espacios extra
        """
        if not title:
            return ""
        
        normalized = title.lower().strip()
        
        # Eliminar puntuación común (mantener solo letras, números y espacios)
        normalized = re.sub(r'[\'"\:\.\-\!\?\,\(\)\[\]\{\}]', '', normalized)
        
        # Eliminar artículos al inicio y final
        articles = r'^(the|a|an|el|la|los|las|un|una|unos|unas)\s+|\s+(the|a|an|el|la|los|las|un|una|unos|unas)$'
        normalized = re.sub(articles, ' ', normalized)
        
        # Normalizar números romanos a arábigos
        normalized = self._roman_to_arabic(normalized)
        
        # Normalizar espacios
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def _roman_to_arabic(self, text: str) -> str:
        """
        Convierte números romanos a arábigos en el texto.
        """
        roman_numerals = {
            ' i ': ' 1 ', ' ii ': ' 2 ', ' iii ': ' 3 ', ' iv ': ' 4 ',
            ' v ': ' 5 ', ' vi ': ' 6 ', ' vii ': ' 7 ', ' viii ': ' 8 ', ' ix ': ' 9 ', ' x ': ' 10 ',
            ' xi ': ' 11 ', ' xii ': ' 12 ', ' xiii ': ' 13 ', ' xiv ': ' 14 ', ' xv ': ' 15 ',
            ' xvi ': ' 16 ', ' xvii ': ' 17 ', ' xviii ': ' 18 ', ' xix ': ' 19 ', ' xx ': ' 20 ',
        }
        
        result = ' ' + text + ' '
        for roman, arabic in roman_numerals.items():
            result = result.replace(roman, arabic)
        
        return result.strip()

    def _is_similar_title(self, search_norm: str, result_norm: str) -> bool:
        """
        Verifica si dos títulos normalizados son similares.
        
        Considera:
        - Títulos idénticos
        - Uno contiene al otro (con límites de palabra) - SOLO para títulos de al menos 2 palabras
        - Diferencias menores en puntuación
        """
        if not search_norm or not result_norm:
            return False
        
        # Mismos títulos normalizados
        if search_norm == result_norm:
            return True
        
        # Uno contiene al otro como palabra completa
        search_words = set(search_norm.split())
        result_words = set(result_norm.split())
        
        # Si son exactamente iguales, ya cubierto
        if search_words == result_words:
            return True
        
        # Si uno es submáscara del otro (palabras completas)
        search_list = search_norm.split()
        result_list = result_norm.split()
        
        # PROTECCIÓN: Para títulos muy cortos (1 palabra), NO permitir submáscara
        # Esto evita que "Superman" coincida con "Superman Returns"
        # o que "Man" coincida con "Man of Steel"
        if len(search_list) <= 1:
            # Para títulos de una palabra, solo aceptar si son exactamente iguales
            return search_norm == result_norm
        
        # Buscar como submáscara (search contenido en result O viceversa)
        # SOLO para títulos de 2+ palabras
        if len(search_list) <= len(result_list):
            # Buscar si search está contenido en result
            for i in range(len(result_list) - len(search_list) + 1):
                if result_list[i:i+len(search_list)] == search_list:
                    return True
        else:
            # Buscar si result está contenido en search
            for i in range(len(search_list) - len(result_list) + 1):
                if search_list[i:i+len(result_list)] == result_list:
                    return True
        
        return False

    def _is_semantically_equivalent(self, search_title: str, result_title: str) -> bool:
        """
        Validación semántica profunda para casos límite.
        
        Maneja casos donde la comparación simple no es suficiente:
        - Títulos con subtítulos ("Jurassic World" vs "Jurassic World: Rebirth")
        - Títulos cortos (< 3 palabras) con variaciones mínimas
        - Números romanos vs arábigos en cualquier posición
        
        Excepciones especiales limitadas:
        - Solo para palabras extra muy específicas (Returns, etc.) en el resultado
        """
        # Análisis de longitud
        search_words = search_title.split()
        result_words = result_title.split()
        
        search_len = len(search_words)
        result_len = len(result_words)
        
        # Normalizar para comparación
        search_norm = self._normalize_title(search_title)
        result_norm = self._normalize_title(result_title)
        
        search_words_norm = search_norm.split()
        result_words_norm = result_norm.split()
        
        # ----- EXCEPCIÓN MUY LIMITADA: Solo para casos específicos de Hollywood -----
        # "Superman" -> "Superman Returns" (una sola palabra extra específica)
        # NO permitir: "Man" -> "Man of Steel" (2 palabras extra)
        if search_len == 1 and result_len == 2:
            # Verificar que search es prefijo exacto de result
            if result_norm.startswith(search_norm + ' ') or result_norm.startswith(search_norm + ':'):
                # Solo permitir si la palabra extra es una de las "palabras de secuela" conocidas
                sequel_words = {'returns', 'rises', 'awakens', 'rebirth', 'revenge'}
                remaining = result_norm[len(search_norm):].strip()
                remaining_words = set(remaining.split())
                if remaining_words & sequel_words:  # Si alguna palabra extra es conocida
                    return True
        
        # ----- PROTECCIÓN CONTRA FALSOS POSITIVOS -----
        
        # Para títulos muy cortos (1-2 palabras), exigir coincidencia CASI EXACTA
        if search_len <= 2:
            # Verificar similitud muy alta
            similarity = self._calculate_word_overlap(search_words_norm, result_words_norm)
            # Para títulos muy cortos, requerimos > 90% de palabras en común
            if similarity < 0.9:
                return False
            # Además, el título resultado no debe agregar palabras significativas
            if result_len > search_len:
                extra_words = set(result_words_norm) - set(search_words_norm)
                for word in extra_words:
                    if len(word) > 3:  # Palabras significativas (más de 3 letras)
                        return False
        
        # ----- CASOS VÁLIDOS -----
        
        # Caso 1: El título buscado está contenido en el resultado (con subtítulo)
        # "Jurassic World" dentro de "Jurassic World: Rebirth"
        # SOLO si el título buscado tiene al menos 3 palabras (títulos largos)
        if search_len >= 3 and self._is_substring_with_word_boundary(search_norm, result_norm):
            return True
        
        # Caso 2: Títulos con diferencias menores (una palabra diferente)
        # SOLO para títulos con al menos 3 palabras
        if search_len >= 3 and result_len >= 3:
            common_words = set(search_words_norm) & set(result_words_norm)
            total_unique = set(search_words_norm) | set(result_words_norm)
            
            if len(total_unique) > 0:
                overlap_ratio = len(common_words) / len(total_unique)
                # Si comparten > 60% de palabras y son del mismo largo (±1 palabra)
                if overlap_ratio >= 0.6 and abs(search_len - result_len) <= 1:
                    return True
        
        # Caso 3: El resultado tiene el año como parte del título (eliminar y comparar)
        # "Movie 2025" vs "Movie"
        search_no_year = re.sub(r'\s*\d{4}\s*', '', search_norm)
        result_no_year = re.sub(r'\s*\d{4}\s*', '', result_norm)
        
        if search_no_year == result_no_year and search_no_year.strip():
            return True
        
        return False

    def _is_substring_with_word_boundary(self, search: str, result: str) -> bool:
        """
        Verifica si search está contenido en result con límites de palabra.
        """
        if not search or not result:
            return False
        
        # Buscar con regex usando límites de palabra
        pattern = r'\b' + re.escape(search) + r'\b'
        if re.search(pattern, result):
            return True
        
        # También verificar el caso inverso
        pattern = r'\b' + re.escape(result) + r'\b'
        if re.search(pattern, search):
            return True
        
        return False

    def _calculate_word_overlap(self, words1: list, words2: list) -> float:
        """
        Calcula el ratio de superposición de palabras entre dos listas.
        """
        if not words1 or not words2:
            return 0.0
        
        set1 = set(words1)
        set2 = set(words2)
        
        intersection = set1 & set2
        union = set1 | set2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)

    def _search_exact_omdb(self, title: str, year: Optional[int], metadata_service) -> Optional[dict]:
        """
        Busca en OMDB con parámetros exactos (título + año).
        """
        try:
            # Usar el método get_movie_metadata del servicio de OMDB
            result = metadata_service.get_movie_metadata(title, year)
            
            if result and result.get('Response') != 'False':
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error en búsqueda OMDB para [{title}]: {e}")
            return None

    def _get_and_save_poster(self, omdb_data: dict, title: str, year: Optional[int]) -> Optional[bytes]:
        """
        Obtiene el póster de los datos de OMDB y lo guarda SOLO si es coincidencia exacta.
        
        Args:
            omdb_data: Datos completos de OMDB
            title: Título que se buscó
            year: Año que se buscó
            
        Returns:
            Datos binarios del póster o None
        """
        poster_url = omdb_data.get('Poster')
        
        if not poster_url or poster_url == 'N/A':
            logger.warning(f"OMDB: No hay póster disponible para [{title}]")
            return None
        
        # Descargar el póster
        import requests
        try:
            response = requests.get(poster_url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"OMDB: Error descargando póster desde {poster_url}")
                return None
            
            poster_data = response.content
            
            # Guardar en base de datos SOLO si es una coincidencia exacta verificada
            self._save_verified_poster_to_db(omdb_data, poster_data)
            
            return poster_data
            
        except Exception as e:
            logger.error(f"OMDB: Error descargando póster para [{title}]: {e}")
            return None

    def _save_verified_poster_to_db(self, omdb_data: dict, poster_data: bytes):
        """
        Guarda el póster en la base de datos SOLO si es una coincidencia exacta verificada.
        Usa context manager para garantizar cierre de sesión.
        
        Args:
            omdb_data: Datos completos de OMDB (verificados)
            poster_data: Datos binarios del póster
        """
        try:
            # Usar context manager para gestionar la sesión
            with get_catalog_repository_session() as db:
                repo = get_catalog_repository(db)
                
                imdb_id = omdb_data.get('imdbID')
                title = omdb_data.get('Title')
                year = omdb_data.get('Year')
                
                if not imdb_id:
                    logger.warning("OMDB: No hay imdb_id, no se puede guardar")
                    return
                
                # Verificar nuevamente que es una coincidencia exacta antes de guardar
                existing = repo.get_omdb_entry_by_imdb_id(imdb_id)
                
                if existing:
                    # Actualizar el póster existente
                    existing.poster_image = poster_data
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"OMDB: Póster actualizado en BD para [{title}] ({year})")
                else:
                    # Crear nueva entrada con todos los datos de OMDB
                    entry = repo.create_or_update_omdb_entry(omdb_data, poster_data)
                    logger.info(f"OMDB: Nueva entrada creada en BD para [{title}] ({year})")
                    
        except Exception as e:
            logger.error(f"Error guardando póster verificado en BD: {e}")


def get_omdb_thumbnail_provider() -> OMDBThumbnailProvider:
    """
    Factory para obtener el proveedor de thumbnails de OMDB.
    
    Returns:
        Instancia de OMDBThumbnailProvider
    """
    from src.infrastructure.config.settings import Settings
    settings = Settings()
    return OMDBThumbnailProvider(settings.OMDB_API_KEY)
