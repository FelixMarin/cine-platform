"""
Cliente de optimización de torrents usando FFmpeg API

Este servicio proporciona métodos para optimizar archivos de video descargados
usando FFmpeg con aceleración GPU NVIDIA a través de una API HTTP externa.

Flujo de optimización:
1. Busca el archivo en las carpetas de Transmission (/downloads/complete/ o /downloads/incomplete/)
2. COPIA el archivo a /shared/input/ (no mueve, para preservar el original)
3. Llama a FFmpeg API con las rutas compartidas
4. Mueve el resultado final a /mnt/DATA_2TB/audiovisual/mkv/{categoría}/
5. Limpia archivos temporales
"""

import os
import logging
import shutil
import threading
import time
import uuid
import requests
from typing import Optional, Dict, Callable, List
from dataclasses import dataclass

from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)

SHARED_INPUT = os.environ.get("SHARED_INPUT_PATH", "/shared/input")
SHARED_OUTPUT = os.environ.get("SHARED_OUTPUT_PATH", "/shared/outputs")


@dataclass
class OptimizationProgress:
    """Representa el progreso de una optimización"""

    process_id: str
    status: str  # 'running', 'done', 'error'
    progress: float  # 0-100
    input_file: str
    output_file: str
    start_time: float
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    logs: str = ""
    # Campos adicionales para metadata
    torrent_id: Optional[int] = None
    category: Optional[str] = None
    original_filename: Optional[str] = None


class TorrentOptimizer:
    """
    Cliente para optimizar archivos de torrent usando FFmpeg API con GPU NVIDIA

    Este optimizador maneja el flujo completo:
    - Busca archivos en carpetas de Transmission
    - Copia a zona compartida para FFmpeg API
    - Procesa y mueve resultado a la categoría final
    """

    # Rutas de Transmission
    TRANSMISSION_COMPLETE = os.environ.get(
        "TRANSMISSION_COMPLETE_PATH", "/downloads/complete"
    )
    TRANSMISSION_INCOMPLETE = os.environ.get(
        "TRANSMISSION_INCOMPLETE_PATH", "/downloads/incomplete"
    )

    def __init__(
        self,
        upload_folder: str = None,
        output_folder: str = None,
        transmission_client=None,
    ):
        """
        Inicializa el optimizador de torrents

        Args:
            upload_folder: Carpeta donde están los archivos descargados (deprecated)
            output_folder: Carpeta donde se guardarán los archivos optimizados
            transmission_client: Cliente de Transmission para obtener info de torrents
        """
        self.upload_folder = upload_folder or settings.UPLOAD_FOLDER
        self.output_folder = output_folder or settings.MOVIES_BASE_PATH
        self.temp_folder = "/tmp/cineplatform/temp"
        self.api_url = os.environ.get("FFMPEG_API_URL", "http://ffmpeg-api:8080")
        self.delete_source = (
            os.environ.get("DELETE_SOURCE_FILE", "true").lower() == "true"
        )
        self.delete_torrent = (
            os.environ.get("DELETE_TORRENT_AFTER_OPTIMIZATION", "true").lower()
            == "true"
        )

        self.transmission_client = transmission_client

        self._processes: Dict[str, OptimizationProgress] = {}
        self._pending: Dict[str, Dict] = {}
        self._lock = threading.Lock()

        os.makedirs(SHARED_INPUT, exist_ok=True)
        os.makedirs(SHARED_OUTPUT, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.temp_folder, exist_ok=True)

        logger.info(f"[TorrentOptimizer] Inicializado. API: {self.api_url}")
        logger.info(
            f"[TorrentOptimizer] Rutas: SHARED_INPUT={SHARED_INPUT}, SHARED_OUTPUT={SHARED_OUTPUT}"
        )

    def _get_file_finder(self):
        """Obtiene el buscador de archivos (inyección de dependencia)"""
        from src.adapters.outgoing.services.file_finder import TransmissionFileFinder

        return TransmissionFileFinder()

    def _get_name_sanitizer(self):
        """Obtiene el sanitizador de nombres (inyección de dependencia)"""
        from src.adapters.outgoing.services.name_sanitizer import StandardSanitizer

        return StandardSanitizer()

    def _get_api_client(self):
        """Obtiene el cliente de API (inyección de dependencia)"""
        from src.adapters.outgoing.services.optimizer_api import FFmpegAPIClient

        return FFmpegAPIClient(self.api_url)

    def _get_cleanup_service(self):
        """Obtiene el servicio de limpieza (inyección de dependencia)"""
        from src.adapters.outgoing.services.cleanup import FileCleanupService

        return FileCleanupService()

    def _find_torrent_file(self, filename: str) -> Optional[str]:
        """
        Busca el archivo en las carpetas de Transmission, probando con extensiones comunes
        si el archivo no se encuentra con el nombre exacto.

        Args:
            filename: Nombre del archivo a buscar (puede incluir o no extensión)

        Returns:
            Ruta completa del archivo si se encuentra, None si no
        """
        search_paths = [self.TRANSMISSION_COMPLETE, self.TRANSMISSION_INCOMPLETE]

        # Intentar con el nombre exacto primero
        for base in search_paths:
            candidate = os.path.join(base, filename)
            logger.debug(f"[TorrentOptimizer] Probando: {candidate}")
            if os.path.exists(candidate):
                logger.debug(f"[TorrentOptimizer] ✓ Archivo encontrado: {candidate}")
                return candidate

        # Si no se encuentra, probar con extensiones comunes
        logger.warning(f"[TorrentOptimizer] Archivo no encontrado con nombre exacto: {filename}")

        common_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.webm', '.m4v']
        for base in search_paths:
            for ext in common_extensions:
                # Si el filename ya termina con la extensión, no añadir
                if filename.lower().endswith(ext):
                    continue
                candidate = os.path.join(base, filename + ext)
                if os.path.exists(candidate):
                    logger.debug(f"[TorrentOptimizer] ✓ Archivo encontrado con extensión añadida: {candidate}")
                    return candidate

        # Si aún no se encuentra, listar archivos en las carpetas para debug
        logger.error(f"[TorrentOptimizer] ✗ Archivo no encontrado después de probar extensiones")
        for base in search_paths:
            if os.path.exists(base):
                try:
                    files = os.listdir(base)
                    logger.debug(f"[TorrentOptimizer] Archivos en {base}: {files[:10]}...")  # Primeros 10
                except Exception as e:
                    logger.warning(f"[TorrentOptimizer] Error listando {base}: {e}")

        return None

    def check_gpu_available(self) -> dict:
        """
        Verifica GPU consultando la API de ffmpeg

        Returns:
            dict con keys:
                - available (bool): True si hay GPU disponible
                - gpu_name (str): Nombre de la GPU o None
                - error (str): Mensaje de error o None
        """
        api_client = self._get_api_client()
        return api_client.check_gpu_available()

    def start_optimization(
        self,
        torrent_id: int,
        category: str,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """
        Inicia optimización de un torrent

        Args:
            torrent_id: ID del torrent en Transmission
            category: Categoría para organizar el archivo final
            filename: Nombre del archivo (opcional). Si se proporciona, se usa directamente
                     para buscar en las carpetas de Transmission sin consultar la API
            progress_callback: Función de callback para progreso

        Returns:
            ID del proceso de optimización

        Raises:
            Exception: Si el archivo no se encuentra
        """
        # Si no se proporciona filename, intentamos obtenerlo de Transmission
        if not filename:
            if not self.transmission_client:
                from src.adapters.outgoing.services.transmission import TransmissionClient

                logger.warning(
                    "[TorrentOptimizer] Transmission client no configurado, creando uno nuevo"
                )
                self.transmission_client = TransmissionClient()

            torrent = self.transmission_client.get_torrent(torrent_id)
            if not torrent:
                raise FileNotFoundError(f"Torrent {torrent_id} no encontrado en Transmission")

            logger.info(
                f"[TorrentOptimizer] Torrent: {torrent.name}, progress={torrent.progress}%"
            )

            progress = (
                (torrent.downloaded_ever / torrent.size_when_done) * 100
                if torrent.size_when_done > 0
                else 0
            )
            if progress < 99.9:
                raise Exception(f"Torrent no completado ({progress:.1f}%)")

            filename = torrent.name
        else:
            logger.info(f"[TorrentOptimizer] Usando filename proporcionado: {filename}")

        # Buscar el archivo en las carpetas de Transmission usando el método mejorado
        source_path = self._find_torrent_file(filename)
        if not source_path:
            raise FileNotFoundError(f"Archivo no encontrado: {filename}")

        name_sanitizer = self._get_name_sanitizer()
        output_filename = name_sanitizer.sanitize(filename)

        shared_input = os.path.join(SHARED_INPUT, filename)
        shutil.copy2(source_path, shared_input)
        logger.info(f"[TorrentOptimizer] Copiado a {shared_input}")

        shared_output = os.path.join(SHARED_OUTPUT, output_filename)

        os.makedirs(SHARED_OUTPUT, exist_ok=True)

        payload = {
            "input": shared_input,
            "output": shared_output,
            "params": [
                "-c:v",
                "h264_nvenc",
                "-preset",
                "p4",
                "-cq",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
            ],
        }

        process_id = str(uuid.uuid4())

        # Crear objeto de progreso ANTES de iniciar el hilo
        progress_obj = OptimizationProgress(
            process_id=process_id,
            status="pending",
            progress=0.0,
            input_file=source_path,
            output_file=shared_output,
            start_time=time.time(),
        )

        with self._lock:
            self._processes[process_id] = progress_obj

        # Guardar metadata SIN el api_process_id aún
        self._pending[process_id] = {
            "output_path": shared_output,
            "category": category,
            "original_filename": filename,
            "final_filename": output_filename,
            "shared_input": shared_input,
            "torrent_id": torrent_id,
            "source_path": source_path,
            "api_process_id": None,  # Se llenará cuando la API responda
            "params": payload["params"],  # Guardar params para reintento si es necesario
        }

        # Lanzar el monitoreo INMEDIATAMENTE - no esperar a que la API responda
        # El monitoreoará el estado y esperará hasta que haya un api_process_id
        thread = threading.Thread(
            target=self._monitor_optimization,
            args=(process_id, None, progress_callback),  # api_process_id puede ser None al inicio
        )
        thread.daemon = True
        thread.start()

        # Lanzar la llamada a la API en un hilo SEPARADO
        # Esto permite que la respuesta HTTP al cliente no se bloquee
        api_thread = threading.Thread(
            target=self._call_api_start,
            args=(process_id, shared_input, shared_output, payload["params"]),
        )
        api_thread.daemon = True
        api_thread.start()

        # Retornar inmediatamente el process_id al cliente
        logger.info(f"[TorrentOptimizer] Optimización iniciada (async): {process_id}")
        return process_id

    def _call_api_start(
        self,
        process_id: str,
        shared_input: str,
        shared_output: str,
        params: list,
    ):
        """
        Hilo separado que hace la llamada HTTP a la API de ffmpeg.
        Actualiza el api_process_id cuando la API responde.
        """
        try:
            api_client = self._get_api_client()
            
            # Esta llamada puede tardar mucho o quedarse colgada si la API no responde bien
            api_process_id = api_client.start_optimization(
                shared_input, shared_output, params
            )

            # Actualizar el api_process_id cuando la API responde
            with self._lock:
                pending = self._pending.get(process_id)
                if pending:
                    pending["api_process_id"] = api_process_id
                    logger.info(f"[TorrentOptimizer] API process_id recibido: {api_process_id}")

        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error al llamar a la API: {e}")
            with self._lock:
                progress = self._processes.get(process_id)
                if progress:
                    progress.status = "error"
                    progress.error_message = f"Error al iniciar optimización: {str(e)}"
                    progress.end_time = time.time()
            
            # Limpiar archivo temporal si falló al iniciar
            if os.path.exists(shared_input):
                try:
                    os.remove(shared_input)
                except Exception:
                    pass

    def _monitor_optimization(
        self,
        local_process_id: str,
        api_process_id: str,
        progress_callback: Optional[Callable] = None,
    ):
        """Monitorea el progreso consultando la API periódicamente"""
        progress = self._processes.get(local_process_id)
        if not progress:
            return

        api_client = self._get_api_client()

        # Si api_process_id es None, esperar hasta que esté disponible
        # Esto permite que el hilo de monitoreo comience antes de que la API responda
        current_api_process_id = api_process_id
        max_wait_for_api = 60  # Máximo 60 segundos esperando el api_process_id
        wait_start = time.time()

        while current_api_process_id is None:
            # Verificar si ya hay un api_process_id
            pending = self._pending.get(local_process_id)
            if pending:
                current_api_process_id = pending.get("api_process_id")
                if current_api_process_id:
                    break
            
            # Verificar si hay un error
            if progress.status == "error":
                logger.warning(f"[TorrentOptimizer] Optimización marcada como error antes de iniciar")
                return

            # Timeout esperando el api_process_id
            if time.time() - wait_start > max_wait_for_api:
                logger.error(f"[TorrentOptimizer] Timeout esperando api_process_id")
                progress.status = "error"
                progress.error_message = "Timeout esperando respuesta de API"
                progress.end_time = time.time()
                return

            time.sleep(0.5)  # Esperar 500ms antes de volver a revisar

        # Actualizar estado a running una vez que tenemos el api_process_id
        if progress.status == "pending":
            progress.status = "running"

        logger.debug(f"[TorrentOptimizer] Monitoreando proceso: {current_api_process_id}")

        while True:
            try:
                api_status = api_client.get_status(current_api_process_id)

                if api_status:
                    progress.status = api_status.get("status", "running")
                    progress.progress = api_status.get("progress", 0)

                    # Capturar mensaje de error si existe
                    if progress.status == "error":
                        error_msg = api_status.get("error", "Error desconocido en FFmpeg")
                        progress.error_message = error_msg
                        progress.end_time = time.time()
                        logger.error(
                            f"[TorrentOptimizer] ❌ Optimización fallida para {local_process_id}: {error_msg}"
                        )
                        # Limpiar recursos y manejar error
                        self._handle_error(local_process_id, error_msg)
                        break

                    logs = api_status.get("logs", [])
                    if logs:
                        progress.logs += "\n".join(logs[-5:]) + "\n"

                    if progress_callback:
                        progress_callback(progress)

                    if progress.status in ["completed", "done"]:
                        progress.end_time = time.time()
                        self._finalize_optimization(local_process_id)
                        break

                time.sleep(int(os.environ.get("OPTIMIZE_POLL_INTERVAL", 2)))

            except Exception as e:
                logger.warning(f"[TorrentOptimizer] Error polling status: {e}")
                time.sleep(5)

    def _finalize_optimization(self, process_id: str):
        """Mueve el archivo optimizado a su destino final y limpia archivos temporales"""
        pending = self._pending.get(process_id)
        if not pending:
            logger.error(
                f"[TorrentOptimizer] No se encontró metadata para proceso {process_id}"
            )
            return

        try:
            output_path = pending["output_path"]
            category = pending["category"]
            original_filename = pending["original_filename"]
            shared_input = pending["shared_input"]
            source_path = pending.get("source_path")
            torrent_id = pending.get("torrent_id")

            # Verificar que el archivo de salida existe antes de proceder
            if not os.path.exists(output_path):
                logger.error(
                    f"[TorrentOptimizer] ❌ Archivo de salida no encontrado: {output_path}. "
                    f"No se realizará la limpieza ni se eliminará el torrent."
                )
                return

            logger.info(
                f"[TorrentOptimizer] ✓ Archivo de salida verificado: {output_path}"
            )

            final_path = os.path.join(
                self.output_folder, category, pending["final_filename"]
            )

            os.makedirs(os.path.dirname(final_path), exist_ok=True)

            shutil.move(output_path, final_path)
            logger.info(f"[TorrentOptimizer] Archivo movido a: {final_path}")

            # Solo limpiar y eliminar torrent si el archivo se movió correctamente
            cleanup_service = self._get_cleanup_service()
            cleanup_service.cleanup(
                shared_input=shared_input,
                source_path=source_path,
                torrent_id=torrent_id,
                transmission_client=self.transmission_client,
            )

            del self._pending[process_id]
            logger.info(
                f"[TorrentOptimizer] ✓ Optimización finalizada para {original_filename}"
            )

        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error finalizando optimización: {e}")

    def _handle_error(self, process_id: str, error_message: str):
        """
        Maneja el error de optimización: limpia archivos temporales y registra el error.
        
        Args:
            process_id: ID del proceso de optimización
            error_message: Mensaje de error detallado
        """
        pending = self._pending.get(process_id)
        if not pending:
            logger.error(
                f"[TorrentOptimizer] No se encontró metadata para proceso {process_id}"
            )
            return

        try:
            original_filename = pending.get("original_filename", "desconocido")
            shared_input = pending.get("shared_input")
            source_path = pending.get("source_path")
            torrent_id = pending.get("torrent_id")

            # Limpiar archivo temporal de entrada
            if shared_input and os.path.exists(shared_input):
                try:
                    os.remove(shared_input)
                    logger.info(f"[TorrentOptimizer] Limpiado archivo temporal: {shared_input}")
                except Exception as e:
                    logger.warning(f"[TorrentOptimizer] Error limpiando {shared_input}: {e}")

            # Limpiar archivo de salida si existe (puede estar parcialmente creado)
            output_path = pending.get("output_path")
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    logger.info(f"[TorrentOptimizer] Limpiado archivo de salida: {output_path}")
                except Exception as e:
                    logger.warning(f"[TorrentOptimizer] Error limpiando {output_path}: {e}")

            # Eliminar el proceso del diccionario de pendientes
            del self._pending[process_id]

            logger.warning(
                f"[TorrentOptimizer] ✓ Optimización fallida para {original_filename}. "
                f"Error: {error_message}"
            )

        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error manejando fallo de optimización: {e}")

    def get_progress(self, process_id: str) -> Optional[OptimizationProgress]:
        """Obtiene el progreso de una optimización (datos locales)"""
        with self._lock:
            return self._processes.get(process_id)

    def get_api_progress(self, process_id: str) -> Optional[Dict]:
        """
        Obtiene progreso detallado desde ffmpeg-api

        Args:
            process_id: ID del proceso local

        Returns:
            Dict con métricas de ffmpeg-api o None si no está disponible
        """
        progress = self._processes.get(process_id)
        if not progress:
            return None

        pending = self._pending.get(process_id)
        api_process_id = pending.get("api_process_id") if pending else None

        if api_process_id:
            try:
                api_client = self._get_api_client()
                api_data = api_client.get_status(api_process_id)
                if api_data:
                    return {
                        "progress": api_data.get("progress", progress.progress),
                        "status": api_data.get("status", progress.status),
                        "fps": api_data.get("fps", 0),
                        "bitrate": api_data.get("bitrate", 0),
                        "current_time": api_data.get("current_time", 0),
                        "eta": api_data.get("eta", 0),
                        "size_formatted": api_data.get("size_formatted", "0 B"),
                        "elapsed": time.time() - progress.start_time
                        if progress.start_time
                        else 0,
                    }
            except Exception as e:
                logger.warning(f"[TorrentOptimizer] Error getting API progress: {e}")

        return {
            "progress": progress.progress,
            "status": progress.status,
            "logs": progress.logs,
            "elapsed": time.time() - progress.start_time if progress.start_time else 0,
            "fps": 0,
            "bitrate": 0,
            "current_time": 0,
            "eta": 0,
            "size_formatted": "0 B",
        }

    def cancel_optimization(self, process_id: str) -> bool:
        """Cancela una optimización en curso"""
        logger.warning(
            f"[TorrentOptimizer] Cancelación no implementada para {process_id}"
        )
        return False

    def list_active(self) -> List[OptimizationProgress]:
        """Lista todas las optimizaciones activas (running, pending, o recientemente completadas)"""
        with self._lock:
            active = []
            for p in self._processes.values():
                if p.status in ["pending", "running", "completed", "done"]:
                    # Enrich with metadata from _pending if available
                    pending = self._pending.get(p.process_id)
                    if pending:
                        # Add extra fields for the API response
                        p.torrent_id = pending.get("torrent_id")
                        p.category = pending.get("category")
                        p.original_filename = pending.get("original_filename")
                    active.append(p)
            return active
