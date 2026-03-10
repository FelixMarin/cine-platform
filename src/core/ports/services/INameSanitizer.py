"""
Puerto para sanitización de nombres de archivos
"""

from abc import ABC, abstractmethod


class INameSanitizer(ABC):
    """Interfaz para sanitizar nombres de archivos"""

    @abstractmethod
    def sanitize(self, filename: str) -> str:
        """
        Sanitiza un nombre de archivo para el output

        Args:
            filename: Nombre original del archivo

        Returns:
            Nombre sanitizado para el archivo de salida
        """
        pass
