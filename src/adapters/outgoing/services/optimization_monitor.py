"""
Servicio de monitoreo de optimizaciones

Maneja el monitoreo del progreso de las optimizaciones en tiempo real.
"""

import logging
import os
import time
import threading
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)


class OptimizationMonitor:
    """Servicio para monitorear el progreso de las optimizaciones"""

    def __init__(self, api_client=None):
        self._api_client = api_client
        self._lock = threading.Lock()

    def _get_api_client(self):
        """Obtiene el cliente de API"""
        if self._api_client is None:
            from src.adapters.outgoing.services.optimizer_api import FFmpegAPIClient

            api_url = os.environ.get("FFMPEG_API_URL", "http://ffmpeg-api:8080")
            self._api_client = FFmpegAPIClient(api_url)
        return self._api_client

    def wait_for_api_process_id(
        self,
        process_id: str,
        pending: dict,
        progress,
        max_wait: int = 60,
    ) -> Optional[str]:
        """
        Espera hasta que el api_process_id esté disponible.

        Args:
            process_id: ID del proceso local
            pending: Diccionario de datos pendientes
            progress: Objeto de progreso
            max_wait: Máximo tiempo de espera en segundos

        Returns:
            El api_process_id cuando esté disponible, o None si hay timeout
        """
        wait_start = time.time()

        while True:
            current_api_process_id = pending.get("api_process_id")
            if current_api_process_id:
                logger.info(
                    f"[Monitor] API process_id obtenido: {current_api_process_id}"
                )
                return current_api_process_id

            if progress.status == "error":
                logger.warning(
                    "[Monitor] Optimización marcada como error antes de iniciar"
                )
                return None

            if time.time() - wait_start > max_wait:
                logger.error("[Monitor] Timeout esperando api_process_id")
                with self._lock:
                    progress.status = "error"
                    progress.error_message = "Timeout esperando respuesta de API"
                    progress.end_time = time.time()
                return None

            time.sleep(0.5)

    def update_progress(
        self,
        progress,
        api_status: dict,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Actualiza el progreso con los datos de la API.

        Args:
            progress: Objeto de progreso
            api_status: Estado devuelto por la API
            progress_callback: Función de callback opcional

        Returns:
            True si la optimización ha terminado, False si continúa
        """
        new_progress = api_status.get("progress", 0)
        new_status = api_status.get("status", "running")

        with self._lock:
            if new_progress != progress.progress:
                logger.info(
                    f"[Monitor] Progreso actualizado: {progress.progress:.1f}% -> {new_progress:.1f}%"
                )
                progress.progress = new_progress

            if new_status != progress.status:
                logger.info(
                    f"[Monitor] Estado cambiado: {progress.status} -> {new_status}"
                )
                progress.status = new_status

        if progress.status == "error":
            error_msg = api_status.get("error", "Error desconocido en FFmpeg")
            with self._lock:
                progress.error_message = error_msg
                progress.end_time = time.time()
            logger.error(f"[Monitor] ❌ Optimización fallida: {error_msg}")
            return True

        logs = api_status.get("logs", [])
        if logs:
            with self._lock:
                progress.logs += "\n".join(logs[-5:]) + "\n"

        if progress_callback:
            progress_callback(progress)

        if progress.status in ["completed", "done"]:
            with self._lock:
                progress.end_time = time.time()
            return True

        return False

    def monitor_loop(
        self,
        local_process_id: str,
        api_process_id: str,
        progress,
        pending: dict,
        progress_callback: Optional[Callable] = None,
    ):
        """
        Bucle principal de monitoreo.

        Args:
            local_process_id: ID del proceso local
            api_process_id: ID del proceso en la API
            progress: Objeto de progreso
            pending: Diccionario de datos pendientes
            progress_callback: Función de callback opcional
        """
        api_client = self._get_api_client()

        with self._lock:
            if progress.status == "pending":
                progress.status = "running"
                logger.info(
                    f"[Monitor] Estado cambiado a 'running' para {local_process_id}"
                )

        logger.info(f"[Monitor] Monitoreando proceso: {api_process_id}")

        while True:
            try:
                api_status = api_client.get_status(api_process_id)

                logger.info(f"[Monitor] Estado API para {api_process_id}: {api_status}")

                if api_status:
                    finished = self.update_progress(
                        progress, api_status, progress_callback
                    )
                    if finished:
                        return

                poll_interval = int(os.environ.get("OPTIMIZE_POLL_INTERVAL", 2))
                time.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"[Monitor] Error polling status: {e}")
                time.sleep(5)
