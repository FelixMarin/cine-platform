"""
Puerto para comunicación con la API de FFmpeg
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IOptimizerAPI(ABC):
    """Interfaz para comunicarse con la API de FFmpeg"""

    @abstractmethod
    def check_gpu_available(self) -> Dict[str, Any]:
        """
        Verifica si hay GPU disponible

        Returns:
            Dict con keys: available (bool), gpu_name (str), error (str)
        """
        pass

    @abstractmethod
    def start_optimization(
        self, input_path: str, output_path: str, params: list
    ) -> str:
        """
        Inicia una optimización

        Args:
            input_path: Ruta del archivo de entrada
            output_path: Ruta del archivo de salida
            params: Parámetros de FFmpeg

        Returns:
            ID del proceso en la API
        """
        pass

    @abstractmethod
    def get_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una optimización

        Args:
            process_id: ID del proceso en la API

        Returns:
            Dict con el estado o None si no existe
        """
        pass
