"""
Implementación de IOptimizerAPI para comunicarse con FFmpeg API
"""

import os
import logging
import requests
from typing import Optional, Dict, Any

from src.core.ports.services.IOptimizerAPI import IOptimizerAPI


logger = logging.getLogger(__name__)


class FFmpegAPIClient(IOptimizerAPI):
    """
    Cliente HTTP para comunicarse con la API de FFmpeg
    """

    def __init__(self, api_url: str = None):
        self.api_url = api_url or os.environ.get(
            "FFMPEG_API_URL", "http://ffmpeg-api:8080"
        )

    def check_gpu_available(self) -> Dict[str, Any]:
        """
        Verifica si hay GPU disponible

        Returns:
            Dict con keys: available (bool), gpu_name (str), error (str)
        """
        try:
            response = requests.get(f"{self.api_url}/gpu-status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                gpu_available = data.get("gpu_available", False)
                gpu_name = data.get("gpu_name") or data.get("gpu_info")
                logger.info(
                    f"[FFmpegAPIClient] GPU disponible: {gpu_available}, nombre: {gpu_name}"
                )
                return {"available": gpu_available, "gpu_name": gpu_name, "error": None}
            return {
                "available": False,
                "gpu_name": None,
                "error": f"API responded {response.status_code}",
            }
        except requests.exceptions.ConnectionError as e:
            logger.warning(
                f"[FFmpegAPIClient] No se pudo conectar a la API de FFmpeg: {e}"
            )
            return {
                "available": False,
                "gpu_name": None,
                "error": "No se pudo conectar a la API de FFmpeg",
            }
        except Exception as e:
            logger.warning(f"[FFmpegAPIClient] Error verificando GPU vía API: {e}")
            return {"available": False, "gpu_name": None, "error": str(e)}

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
        payload = {
            "input": input_path,
            "output": output_path,
            "params": params,
        }

        # Timeout más largo: 10 minutos (600 segundos)
        # Esto permite que la API tenga tiempo de procesar archivos grandes
        # La conexión se cierra cuando la API termina el trabajo
        response = requests.post(
            f"{self.api_url}/optimize", 
            json=payload, 
            timeout=600  # 10 minutos
        )

        if response.status_code != 200:
            error_msg = response.json().get("error", "Error desconocido")
            raise RuntimeError(f"Error en API: {error_msg}")

        data = response.json()
        return data.get("process_id")

    def get_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una optimización

        Args:
            process_id: ID del proceso en la API

        Returns:
            Dict con el estado o None si no existe
        """
        try:
            response = requests.get(f"{self.api_url}/status/{process_id}", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"[FFmpegAPIClient] Error obteniendo estado: {e}")
        return None
