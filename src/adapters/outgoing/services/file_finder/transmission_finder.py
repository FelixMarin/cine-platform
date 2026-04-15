"""
Implementación de IFileFinder para buscar archivos de Transmission
"""

import logging
import os
from typing import List, Optional

from src.domain.ports.out.services.IFileFinder import IFileFinder

logger = logging.getLogger(__name__)


TRANSMISSION_COMPLETE = os.environ.get(
    "TRANSMISSION_COMPLETE_PATH", "/mnt/DATA_2TB/administracion-peliculas/complete"
)
TRANSMISSION_INCOMPLETE = os.environ.get(
    "TRANSMISSION_INCOMPLETE_PATH", "/mnt/DATA_2TB/administracion-peliculas/incomplete"
)


class TransmissionFileFinder(IFileFinder):
    """
    Implementación que busca archivos en las carpetas de Transmission
    """

    def __init__(self):
        self.search_paths = [
            TRANSMISSION_COMPLETE,
            TRANSMISSION_INCOMPLETE,
        ]

    def find_file(self, filename: str) -> Optional[str]:
        """
        Busca un archivo en las ubicaciones de Transmission

        Args:
            filename: Nombre del archivo a buscar

        Returns:
            Ruta completa del archivo si se encuentra, None si no
        """
        logger.info(f"[TransmissionFileFinder] Buscando archivo: '{filename}'")

        for path in self.search_paths:
            full_path = os.path.join(path, filename)
            logger.info(f"[TransmissionFileFinder] Probando: {full_path}")

            if os.path.exists(full_path):
                logger.info(f"[TransmissionFileFinder] ✓ ENCONTRADO: {full_path}")
                return full_path

        logger.warning(f"[TransmissionFileFinder] Archivo no encontrado: {filename}")
        self._log_available_files()

        return None

    def list_files(self, directory: str) -> List[str]:
        """
        Lista archivos en un directorio (recursivo)

        Args:
            directory: Ruta del directorio

        Returns:
            Lista de rutas completas de archivos
        """
        result = []
        try:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for f in files:
                        result.append(os.path.join(root, f))
        except Exception as e:
            logger.error(f"[TransmissionFileFinder] Error listando {directory}: {e}")
        return result

    def file_exists(self, path: str) -> bool:
        """Verifica si un archivo existe"""
        return os.path.exists(path)

    def get_file_size(self, path: str) -> int:
        """Obtiene el tamaño de un archivo en bytes"""
        return os.path.getsize(path)

    def _log_available_files(self):
        """Registra los archivos disponibles en las carpetas de búsqueda"""
        for dir_path in self.search_paths:
            logger.warning(f"[TransmissionFileFinder] Archivos en {dir_path}:")
            try:
                if os.path.exists(dir_path):
                    for f in os.listdir(dir_path):
                        logger.warning(f"  - {f}")
                else:
                    logger.warning("  [DIR NO EXISTE]")
            except Exception as e:
                logger.warning(f"  [ERROR: {e}]")
