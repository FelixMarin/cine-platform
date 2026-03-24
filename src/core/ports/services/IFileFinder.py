"""
Puerto para encontrar archivos de torrent en el sistema de archivos
"""

from abc import ABC, abstractmethod
from typing import Optional, List


class IFileFinder(ABC):
    """Interfaz para buscar archivos en el sistema de archivos"""

    @abstractmethod
    def find_file(self, filename: str) -> Optional[str]:
        """
        Busca un archivo por nombre en las ubicaciones configuradas

        Args:
            filename: Nombre del archivo a buscar

        Returns:
            Ruta completa del archivo si se encuentra, None si no
        """
        pass

    @abstractmethod
    def list_files(self, directory: str) -> List[str]:
        """
        Lista archivos en un directorio

        Args:
            directory: Ruta del directorio

        Returns:
            Lista de nombres de archivos
        """
        pass
