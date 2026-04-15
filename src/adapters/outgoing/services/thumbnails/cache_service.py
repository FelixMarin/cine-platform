"""
Servicio de caché de thumbnails

Responsabilidad: Almacenar y recuperar thumbnails del sistema de archivos.
Proporciona una capa de caché para evitar descargas repetidas de OMDB.
"""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ThumbnailCacheService:
    """Servicio para gestionar el caché de thumbnails en el sistema de archivos"""

    def __init__(self, cache_folder: str):
        """
        Inicializa el servicio de caché.
        
        Args:
            cache_folder: Ruta a la carpeta de thumbnails (contiene subcarpeta 'cache')
        """
        self.cache_folder = cache_folder
        self.cache_dir = os.path.join(cache_folder, 'cache')

    def get_cache_path(self, title: str, year: Optional[str]) -> str:
        """
        Genera la ruta de caché para un título/año.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            
        Returns:
            Ruta completa al archivo de caché
        """
        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title.lower())
        year_str = year if year else 'unknown'
        cache_filename = f"{safe_title}_{year_str}.jpg"
        return os.path.join(self.cache_dir, cache_filename)

    def get_cached_thumbnail(self, title: str, year: Optional[str]) -> Optional[str]:
        """
        Recupera la ruta del thumbnail de caché si existe.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            
        Returns:
            Ruta al archivo de caché si existe, None en caso contrario
        """
        cache_path = self.get_cache_path(title, year)

        if os.path.exists(cache_path):
            logger.info(f"CACHE: Sirviendo poster para [{title}] desde archivo caché")
            return cache_path

        return None

    def save_thumbnail(self, title: str, year: Optional[str], data: bytes) -> Optional[str]:
        """
        Guarda el thumbnail en el caché del sistema de archivos.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            data: Datos binarios de la imagen
            
        Returns:
            Ruta donde se guardó el archivo, o None si hubo error
        """
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            cache_path = self.get_cache_path(title, year)

            with open(cache_path, 'wb') as f:
                f.write(data)

            logger.info(f"CACHE: Guardado poster en [{cache_path}]")
            return cache_path

        except Exception as e:
            logger.error(f"CACHE: Error guardando en caché: {e}")
            return None

    def exists(self, title: str, year: Optional[str]) -> bool:
        """
        Verifica si existe un thumbnail en caché.
        
        Args:
            title: Título de la película
            year: Año de la película (opcional)
            
        Returns:
            True si existe el caché, False en caso contrario
        """
        cache_path = self.get_cache_path(title, year)
        return os.path.exists(cache_path)


def get_thumbnail_cache_service() -> ThumbnailCacheService:
    """
    Factory para obtener el servicio de caché de thumbnails.
    
    Returns:
        Instancia de ThumbnailCacheService
    """
    from src.infrastructure.config.settings import Settings
    settings = Settings()
    return ThumbnailCacheService(settings.THUMBNAIL_FOLDER)
