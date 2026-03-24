"""
Servicio de thumbnails desde base de datos

Responsabilidad: Obtener thumbnails desde el campo poster_image 
de las tablas omdb_entries y local_content en la base de datos.
Con caché en memoria para evitar saturación del pool de conexiones.

FLUJO DE BÚSQUEDA:
1. omdb_entries (contenido con IMDB ID)
2. local_content (contenido manual SIN IMDB ID)
"""

import logging
import re
from typing import Optional

from src.adapters.outgoing.services.thumbnails.memory_cache import get_thumbnail_cache
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)

logger = logging.getLogger(__name__)


class DatabaseThumbnailService:
    """Servicio para obtener thumbnails desde base de datos con búsqueda exacta y caché"""

    def __init__(self, catalog_repository):
        """
        Inicializa el servicio de thumbnails de base de datos.
        
        Args:
            catalog_repository: Instancia de CatalogRepository
        """
        self.catalog_repository = catalog_repository
        self.cache = get_thumbnail_cache()

    def _get_thumbnail_from_omdb_entries(self, title: str, year: Optional[str], db) -> Optional[bytes]:
        """
        Busca thumbnail en omdb_entries.
        
        Args:
            title: Título de la película/serie
            year: Año de lanzamiento (opcional)
            db: Sesión de base de datos
            
        Returns:
            Datos binarios de la imagen (poster_image) o None si no existe
        """
        from src.infrastructure.models.catalog import OmdbEntry
        from sqlalchemy import func
        
        try:
            # INTENTAR COINCIDENCIA EXACTA (título limpio + año)
            entry = self._get_exact_match_by_cleaned_title_omdb(title, year, db)
            if entry and entry.poster_image:
                logger.info(f"✅ Coincidencia exacta en omdb_entries (título limpio): {entry.title} ({entry.year})")
                return entry.poster_image
            
            # INTENTAR COINCIDENCIA EXACTA CON EL TÍTULO ORIGINAL
            entry = self._get_exact_match_omdb(title, year, db)
            if entry and entry.poster_image:
                logger.info(f"✅ Coincidencia exacta en omdb_entries (título original): {entry.title} ({entry.year})")
                return entry.poster_image
            
            return None
        except Exception as e:
            logger.error(f"DB: Error buscando en omdb_entries: {e}")
            return None

    def _get_thumbnail_from_local_content(self, title: str, year: Optional[str], db) -> Optional[bytes]:
        """
        Busca thumbnail en local_content (para contenido sin IMDB ID).
        
        Args:
            title: Título de la película/serie
            year: Año de lanzamiento (opcional)
            db: Sesión de base de datos
            
        Returns:
            Datos binarios de la imagen (poster_image) o None si no existe
        """
        from src.infrastructure.models.catalog import LocalContent
        from sqlalchemy import func
        
        try:
            # Limpiar título: quitar año entre paréntesis (ej: "Nazi Supersoldier (2023)" -> "Nazi Supersoldier")
            # Usar raw string para la regex
            cleaned_title = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            
            # Buscar en local_content donde type = 'movie' o 'series'
            # Primero intentar coincidencia exacta con año y título limpio
            query = db.query(LocalContent).filter(
                func.lower(LocalContent.title) == func.lower(cleaned_title)
            )
            
            if year:
                query = query.filter(LocalContent.year == str(year))
            
            # Primero buscar películas
            entry = query.filter(LocalContent.type == 'movie').first()
            if entry and entry.poster_image:
                logger.info(f"✅ Thumbnail encontrado en local_content (movie): {entry.title} ({entry.year})")
                return entry.poster_image
            
            # Luego buscar series
            entry = query.filter(LocalContent.type == 'series').first()
            if entry and entry.poster_image:
                logger.info(f"✅ Thumbnail encontrado en local_content (series): {entry.title} ({entry.year})")
                return entry.poster_image
            
            # Si no hay coincidencia exacta con año, buscar sin año pero con título limpio
            if year:
                query_no_year = db.query(LocalContent).filter(
                    func.lower(LocalContent.title) == func.lower(cleaned_title),
                    LocalContent.type == 'movie'
                )
                entry = query_no_year.first()
                if entry and entry.poster_image:
                    logger.info(f"✅ Thumbnail encontrado en local_content (movie, sin año): {entry.title} ({entry.year})")
                    return entry.poster_image
            
            # INTENTAR CON TÍTULO ORIGINAL (sin limpieza) como fallback
            query_original = db.query(LocalContent).filter(
                func.lower(LocalContent.title) == func.lower(title.strip())
            )
            
            if year:
                query_original = query_original.filter(LocalContent.year == str(year))
            
            entry = query_original.filter(LocalContent.type == 'movie').first()
            if entry and entry.poster_image:
                logger.info(f"✅ Thumbnail encontrado en local_content (movie, título original): {entry.title} ({entry.year})")
                return entry.poster_image
            
            entry = query_original.filter(LocalContent.type == 'series').first()
            if entry and entry.poster_image:
                logger.info(f"✅ Thumbnail encontrado en local_content (series, título original): {entry.title} ({entry.year})")
                return entry.poster_image
            
            return None
        except Exception as e:
            logger.error(f"DB: Error buscando en local_content: {e}")
            return None

    def _get_exact_match_omdb(self, title: str, year: Optional[str], db):
        """Busca coincidencia exacta en omdb_entries"""
        from src.infrastructure.models.catalog import OmdbEntry
        from sqlalchemy import func
        
        query = db.query(OmdbEntry).filter(
            func.lower(OmdbEntry.title) == func.lower(title.strip())
        )
        
        if year:
            query = query.filter(OmdbEntry.year == str(year))
        
        return query.first()

    def _get_exact_match_by_cleaned_title_omdb(self, raw_title: str, year: Optional[str], db):
        """
        Extrae el título limpio (sin años entre paréntesis) y busca coincidencia exacta en omdb_entries.
        """
        from src.infrastructure.models.catalog import OmdbEntry
        from sqlalchemy import func
        
        # Limpiar título: quitar año entre paréntesis
        cleaned_title = re.sub(r'\s*\(\d{4}\)\s*$', '', raw_title).strip()
        
        if not cleaned_title:
            return None
        
        query = db.query(OmdbEntry).filter(
            func.lower(OmdbEntry.title) == func.lower(cleaned_title)
        )
        
        if year:
            query = query.filter(OmdbEntry.year == str(year))
        
        return query.first()

    def get_thumbnail_from_db(self, title: str, year: Optional[str] = None) -> Optional[bytes]:
        """
        Obtiene thumbnail con búsqueda EXACTA y caché en memoria.
        NUNCA usa búsqueda parcial - si no hay coincidencia exacta, devuelve None.
        El orquestador se encargará de llamar a OMDB para obtener la imagen correcta.
        
        FLUJO DE BÚSQUEDA (por orden de prioridad):
        1. omdb_entries (contenido con IMDB ID)
        2. local_content (contenido manual SIN IMDB ID)
        
        Args:
            title: Título de la película/serie
            year: Año de lanzamiento (opcional)
            
        Returns:
            Datos binarios de la imagen (poster_image) o None si no existe
        """
        try:
            logger.info(f"🔍 Buscando thumbnail para: [{title}] año=[{year}]")
            
            # 1. INTENTAR CACHÉ EN MEMORIA (0 conexiones a BBDD)
            cached_data = self.cache.get(title, year)
            if cached_data:
                logger.info(f"✅ Caché HIT para {title} ({year})")
                return cached_data
            
            # Convertir año a int si existe
            year_int = int(year) if year and year.isdigit() else None
            
            # 2. Usar context manager para la sesión de base de datos
            with get_catalog_repository_session() as db:
                # 2.1 PRIMERO: Buscar en omdb_entries (prioridad para contenido con IMDB)
                thumbnail_data = self._get_thumbnail_from_omdb_entries(title, year, db)
                if thumbnail_data:
                    # Guardar en caché
                    self.cache.set(title, year, thumbnail_data)
                    return thumbnail_data
                
                # 2.2 SEGUNDO: Buscar en local_content (fallback para contenido sin IMDB)
                logger.info(f"🔍 No encontrado en omdb_entries, buscando en local_content para [{title}]")
                thumbnail_data = self._get_thumbnail_from_local_content(title, year, db)
                if thumbnail_data:
                    # Guardar en caché
                    self.cache.set(title, year, thumbnail_data)
                    return thumbnail_data
                
                # NO HAY FALLBACK - Si no hay coincidencia exacta, devolver None
                # El orquestador llamará a OMDB para obtener la imagen correcta
                logger.info(f"❌ No hay coincidencia exacta para {title} ({year}) en ninguna tabla")
                return None
            
        except Exception as e:
            logger.error(f"DB: Error buscando thumbnail en BD para {title}: {e}")
            return None


def get_database_thumbnail_service():
    """
    Factory para obtener el servicio de thumbnails desde base de datos.
    
    Returns:
        Instancia de DatabaseThumbnailService
    
    Nota: Este servicio ahora usa context manager internamente,
    por lo que no necesita mantener una referencia al repositorio.
    """
    # Ya no necesitamos crear el repo aquí - se crea una nueva sesión por operación
    return DatabaseThumbnailService(None)
