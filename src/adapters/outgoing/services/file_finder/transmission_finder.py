"""
Implementación de IFileFinder para buscar archivos de Transmission
"""

import os
import logging
from typing import Optional, List

from src.core.ports.services.IFileFinder import IFileFinder


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
        Lista archivos en un directorio

        Args:
            directory: Ruta del directorio

        Returns:
            Lista de nombres de archivos
        """
        try:
            if os.path.exists(directory):
                return [
                    f
                    for f in os.listdir(directory)
                    if os.path.isfile(os.path.join(directory, f))
                ]
        except Exception as e:
            logger.error(f"[TransmissionFileFinder] Error listando {directory}: {e}")
        return []

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
