"""
Puerto para limpieza de archivos temporales
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ICleanupService(ABC):
    """Interfaz para limpiar archivos temporales después de optimización"""

    @abstractmethod
    def cleanup(
        self,
        shared_input: Optional[str] = None,
        source_path: Optional[str] = None,
        torrent_id: Optional[int] = None,
        transmission_client: Any = None,
    ) -> Dict[str, Any]:
        """
        Limpia archivos temporales y opcionalmente elimina el torrent

        Args:
            shared_input: Ruta del archivo temporal en /shared/input/
            source_path: Ruta del archivo fuente original
            torrent_id: ID del torrent en Transmission
            transmission_client: Cliente de Transmission

        Returns:
            Dict con resultados de la limpieza
        """
        pass
