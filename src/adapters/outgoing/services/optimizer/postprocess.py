"""
Post-procesamiento de optimización - Mover archivos a su ubicación final
"""

import logging
import os
import shutil
from typing import Dict

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class PostProcessor:
    """
    Gestiona el movimiento de archivos optimizados a su ubicación final
    """

    # Mapeo de categorías a carpetas
    CATEGORY_PATHS = {
        "Acción": "accion",
        "Animación": "animacion",
        "Aventura": "aventura",
        "Ciencia Ficción": "sci_fi",
        "Comedia": "comedia",
        "Documental": "documental",
        "Drama": "drama",
        "Familia": "familia",
        "Fantasía": "fantasia",
        "Historia": "historia",
        "Música": "musica",
        "Misterio": "misterio",
        "Romance": "romance",
        "Suspense": "suspense",
        "Terror": "terror",
        "Western": "western",
        "Otro": "otros",
    }

    def __init__(self):
        self.movies_folder = settings.MOVIES_FOLDER
        self.upload_folder = settings.UPLOAD_FOLDER

    def get_final_path(self, category: str, filename: str) -> str:
        """
        Calcula la ruta final para un archivo

        Args:
            category: Categoría de la película
            filename: Nombre del archivo

        Returns:
            Ruta completa donde se moverá el archivo
        """
        # Normalizar categoría
        folder_name = self.CATEGORY_PATHS.get(category, "other")

        # Construir ruta final
        final_dir = os.path.join(self.movies_folder, "mkv", folder_name)
        os.makedirs(final_dir, exist_ok=True)

        return os.path.join(final_dir, filename)

    def move_to_final(
        self, source_path: str, category: str, original_filename: str
    ) -> Dict:
        """
        Mueve un archivo optimizado a su ubicación final

        Args:
            source_path: Ruta actual del archivo optimizado
            category: Categoría seleccionada
            original_filename: Nombre original para el archivo final

        Returns:
            Diccionario con resultado de la operación
        """
        logger.info(f"[PostProcess] Moviendo {source_path} a categoría {category}")

        # Verificar que existe el archivo fuente
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Archivo no encontrado: {source_path}")

        # Determinar nombre final
        final_filename = self._get_unique_filename(category, original_filename)
        final_path = self.get_final_path(category, final_filename)

        logger.info(f"[PostProcess] Ruta final: {final_path}")

        # Mover archivo
        try:
            shutil.move(source_path, final_path)
            logger.info("[PostProcess] Archivo movido exitosamente")

            return {
                "success": True,
                "source": source_path,
                "destination": final_path,
                "category": category,
                "filename": final_filename,
                "size": os.path.getsize(final_path),
            }

        except Exception as e:
            logger.error(f"[PostProcess] Error al mover: {str(e)}")
            raise

    def _get_unique_filename(self, category: str, filename: str) -> str:
        """
        Genera un nombre de archivo único, evitando duplicados

        Args:
            category: Categoría
            filename: Nombre deseado

        Returns:
            Nombre de archivo único
        """
        folder_name = self.CATEGORY_PATHS.get(category, "other")
        final_dir = os.path.join(self.movies_folder, "mkv", folder_name)

        # Obtener nombre base y extensión
        name, ext = os.path.splitext(filename)
        if not ext:
            ext = ".mkv"

        final_path = os.path.join(final_dir, filename)

        # Si no existe, usar ese nombre
        if not os.path.exists(final_path):
            return filename

        # Añadir sufijo hasta encontrar nombre único
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_path = os.path.join(final_dir, new_filename)
            if not os.path.exists(new_path):
                logger.info(f"[PostProcess] Nombre duplicado, usando: {new_filename}")
                return new_filename
            counter += 1

            # Límite de reintentos
            if counter > 100:
                raise RuntimeError(f"No se pudo encontrar nombre único para {filename}")

    def cleanup_temp_files(self, file_path: str, related_files: list = None):
        """
        Limpia archivos temporales relacionados

        Args:
            file_path: Ruta del archivo principal
            related_files: Lista de archivos relacionados a eliminar
        """
        logger.info("[PostProcess] Limpiando archivos temporales")

        cleaned = []
        errors = []

        # Limpiar archivo principal si está en carpeta temporal
        if file_path.startswith(self.upload_folder):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned.append(file_path)
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")

        # Limpiar archivos relacionados
        if related_files:
            for f in related_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                        cleaned.append(f)
                except Exception as e:
                    errors.append(f"{f}: {str(e)}")

        logger.info(f"[PostProcess] Limpiados: {len(cleaned)} archivos")
        if errors:
            logger.warning(f"[PostProcess] Errores al limpiar: {errors}")

        return {"cleaned": cleaned, "errors": errors}


class CatalogUpdater:
    """
    Actualiza el catálogo después de mover un archivo
    """

    def __init__(self):
        from src.adapters.outgoing.repositories.filesystem.movie_repository import (
            FilesystemMovieRepository,
        )

        self.movie_repo = FilesystemMovieRepository(settings.MOVIES_FOLDER)

    def refresh_category(self, category: str):
        """
        Refresca el caché de una categoría específica

        Args:
            category: Categoría a refrescar
        """
        logger.info(f"[Catalog] Refrescando categoría: {category}")
        # La implementación real dependería del sistema de caché
        # Por ahora registramos la acción
        logger.info(f"[Catalog] Caché invalidado para categoría: {category}")

    def register_movie(self, file_path: str, category: str) -> Dict:
        """
        Registra una nueva película en el catálogo

        Args:
            file_path: Ruta del archivo
            category: Categoría

        Returns:
            Información de la película registrada
        """
        logger.info(f"[Catalog] Registrando película: {file_path}")

        # Extraer metadatos básicos del archivo
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]

        # Aquí se podrían obtener más metadatos con ffprobe
        # Por ahora solo registramos la información básica

        return {
            "success": True,
            "filename": filename,
            "title": title,
            "category": category,
            "path": file_path,
        }


def process_completed_optimization(job_id: str, job_data: Dict) -> Dict:
    """
    Procesa una optimización completada:
    1. Mueve el archivo a su ubicación final
    2. Actualiza el catálogo
    3. Limpia archivos temporales

    Args:
        job_id: ID del trabajo
        job_data: Datos del trabajo de optimización

    Returns:
        Resultado del procesamiento
    """
    logger.info(f"[PostProcess] Procesando optimización completada: {job_id}")

    result = {
        "job_id": job_id,
        "moved": False,
        "catalog_updated": False,
        "cleaned": False,
        "errors": [],
    }

    try:
        # Obtener información del trabajo
        output_path = job_data.get("output_path")
        category = job_data.get("category", "Drama")
        original_filename = job_data.get("original_filename")

        if not original_filename:
            original_filename = os.path.basename(output_path)

        # 1. Mover archivo a ubicación final
        if output_path and os.path.exists(output_path):
            post_processor = PostProcessor()
            move_result = post_processor.move_to_final(
                source_path=output_path,
                category=category,
                original_filename=original_filename,
            )
            result["moved"] = True
            result["final_path"] = move_result["destination"]

            # 2. Actualizar catálogo
            try:
                updater = CatalogUpdater()
                updater.refresh_category(category)
                updater.register_movie(
                    file_path=move_result["destination"], category=category
                )
                result["catalog_updated"] = True
            except Exception as e:
                logger.error(f"[PostProcess] Error actualizando catálogo: {e}")
                result["errors"].append(f"Catalog update: {str(e)}")

            # 3. Limpiar temporales
            try:
                post_processor.cleanup_temp_files(output_path)
                result["cleaned"] = True
            except Exception as e:
                logger.warning(f"[PostProcess] Error limpiando: {e}")
                result["errors"].append(f"Cleanup: {str(e)}")

        else:
            result["errors"].append(f"Output file not found: {output_path}")

    except Exception as e:
        logger.error(f"[PostProcess] Error procesando optimización: {str(e)}")
        result["errors"].append(str(e))

    logger.info(f"[PostProcess] Resultado: {result}")
    return result
