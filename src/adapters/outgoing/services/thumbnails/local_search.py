"""
Servicio de búsqueda local de thumbnails

Responsabilidad: Buscar thumbnails en el sistema de archivos local.
Este servicio es el FALLBACK FINAL, solo se usa cuando no se encuentra
la imagen en la base de datos (poster_image) ni en OMDB.

Uso previsto:
- Thumbnails generados manualmente
- Imágenes guardadas en static/thumbnails/
- Último recurso cuando BD y OMDB no tienen la imagen
"""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LocalThumbnailSearch:
    """Servicio para buscar thumbnails en el sistema de archivos local"""

    def __init__(self, thumbnail_folder: str):
        """
        Inicializa el servicio de búsqueda local.
        
        Args:
            thumbnail_folder: Ruta a la carpeta de thumbnails
        """
        self.thumbnail_folder = thumbnail_folder

    def search_local_thumbnail(
        self,
        title: str,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Busca thumbnail en la carpeta local por título o filename.
        
        Args:
            title: Título de la película
            filename: Nombre del archivo de video (opcional)
            
        Returns:
            Ruta relativa al thumbnail (para servir por URL) o None si no se encontró
        """
        # Extraer nombre base del filename o del título
        if filename:
            # El filename ya tiene el nombre completo (ej: Red-One-(2023)-optimized.mkv)
            # Usar tal cual pero sin extensión - NO hacer limpieza
            base_name = os.path.splitext(filename)[0]
        else:
            # Limpiar el título para crear nombre de archivo
            base_name = self._sanitize_title(title)

        # Construir nombres de archivo a buscar
        # Si base_name ya termina en -optimized, no agregar otro
        search_names = []
        if not base_name.lower().endswith('optimized'):
            search_names.extend([
                f"{base_name}-optimized.jpg",
                f"{base_name}-optimized.webp"
            ])
        search_names.extend([
            f"{base_name}.jpg",
            f"{base_name}.webp"
        ])

        local_thumbnail_path = None
        found_filename = None

        for search_name in search_names:
            local_path = os.path.join(self.thumbnail_folder, search_name)
            if os.path.exists(local_path):
                local_thumbnail_path = local_path
                found_filename = search_name
                break

        if local_thumbnail_path and found_filename:
            logger.info(f"✅ Thumbnail local encontrado: [{found_filename}]")
            return f"/thumbnails/{found_filename}"

        logger.info(f"⚠️ No se encontró thumbnail local para [{title}]")
        return None

    def _sanitize_title(self, title: str) -> str:
        """
        Limpia el título para crear un nombre de archivo válido.
        
        Args:
            title: Título de la película
            
        Returns:
            Título sanitizado para nombre de archivo
        """
        # Eliminar año entre paréntesis o al final
        base_name = re.sub(r'\s*\(?\d{4}\)?\s*$', '', title)
        # Eliminar sufijos comunes PERO mantener -optimized si es parte del nombre
        base_name = re.sub(r'[-_](optimized|hd|bluray|webrip|web-dl)$', '', base_name, flags=re.IGNORECASE)
        # Eliminar patrones restantes de (año)
        base_name = re.sub(r'\s*\([^)]*\)\s*', ' ', base_name)
        # Limpiar espacios
        base_name = re.sub(r'\s+', ' ', base_name).strip()

        return base_name


def get_local_thumbnail_search() -> LocalThumbnailSearch:
    """
    Factory para obtener el servicio de búsqueda local de thumbnails.
    
    Returns:
        Instancia de LocalThumbnailSearch
    """
    from src.infrastructure.config.settings import Settings
    settings = Settings()
    return LocalThumbnailSearch(settings.THUMBNAIL_FOLDER)
