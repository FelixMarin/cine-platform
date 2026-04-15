"""
Puerto para interactuar con el sistema de archivos
"""

from abc import ABC, abstractmethod
from typing import Optional, List


class IFileFinder(ABC):
    """Puerto para buscar y consultar archivos en el sistema de archivos"""

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
        Lista archivos en un directorio (recursivo)

        Args:
            directory: Ruta del directorio

        Returns:
            Lista de rutas completas de archivos
        """
        pass

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """
        Verifica si un archivo existe

        Args:
            path: Ruta del archivo

        Returns:
            True si existe, False en caso contrario
        """
        pass

    @abstractmethod
    def get_file_size(self, path: str) -> int:
        """
        Obtiene el tamaño de un archivo en bytes

        Args:
            path: Ruta del archivo

        Returns:
            Tamaño en bytes
        """
        pass
