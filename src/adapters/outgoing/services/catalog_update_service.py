"""
Servicio de actualización del catálogo

Maneja la actualización de la base de datos del catálogo con nuevo contenido optimizado.
"""

import logging
import os

from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)

logger = logging.getLogger(__name__)


class CatalogUpdateService:
    """Servicio para actualizar el catálogo con nuevo contenido"""

    def update_catalog(
        self,
        file_path: str,
        category: str,
        metadata: dict,
    ):
        """
        Actualiza la base de datos del catálogo con la nueva película optimizada.

        Args:
            file_path: Ruta completa del archivo en el catálogo
            category: Categoría de la película (action, horror, sci_fi, etc.)
            metadata: Metadatos del proceso de optimización
        """
        try:
            with get_catalog_repository_session() as db:
                repo = get_catalog_repository(db)

                filename = metadata.get("final_filename", "")
                title = (
                    filename.replace("-optimized", "")
                    .replace(".mkv", "")
                    .replace("-", " ")
                    .title()
                )

                file_size = 0
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)

                existing = repo.get_local_content_by_file_path(file_path)

                if existing:
                    logger.info(
                        f"[CatalogUpdateService] Actualizando registro existente en catálogo: {existing.id}"
                    )
                else:
                    content_data = {
                        "title": title,
                        "file_path": file_path,
                        "file_size": file_size,
                        "type": "movie",
                        "genre": category,
                        "is_optimized": True,
                        "quality": "optimized",
                        "format": "mkv",
                    }

                    try:
                        new_content = repo.create_local_content(content_data)
                        logger.info(
                            f"[CatalogUpdateService] ✅ Nuevo contenido registrado en catálogo: {new_content.id} - {title}"
                        )
                    except Exception as create_error:
                        logger.warning(
                            f"[CatalogUpdateService] ⚠️ Error creando contenido en catálogo: {create_error}"
                        )

        except Exception as e:
            logger.warning(f"[CatalogUpdateService] ⚠️ Error en update_catalog: {e}")
