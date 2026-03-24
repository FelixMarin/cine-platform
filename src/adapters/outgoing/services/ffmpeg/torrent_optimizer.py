"""
Cliente de optimización de torrents usando FFmpeg API

Este servicio proporciona métodos para optimizar archivos de video descargados
usando FFmpeg con aceleración GPU NVIDIA a través de una API HTTP externa.

Flujo de optimización:
1. Obtiene la ruta del archivo desde Transmission
2. USA DIRECTAMENTE el archivo original como input (sin copiar)
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
from src.adapters.outgoing.services.optimization_history_service import (
    OptimizationHistoryService,
)
from src.adapters.outgoing.services.catalog_update_service import CatalogUpdateService
from src.adapters.outgoing.services.optimization_monitor import OptimizationMonitor
from src.adapters.outgoing.services.optimization_error_handler import (
    OptimizationErrorHandler,
)
from src.adapters.outgoing.services.torrent_file_finder import TorrentFileFinder


logger = logging.getLogger(__name__)

SHARED_INPUT = os.environ.get("SHARED_INPUT_PATH", "/app/uploads")
SHARED_OUTPUT = os.environ.get("SHARED_OUTPUT_PATH", "/app/outputs")


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

    # Rutas CORRECTAS donde debe buscar el optimizador (IGNORAR downloadDir de Transmission)
    # Estas son las rutas DENTRO del contenedor cine-platform/transmission
    # El mount es: /mnt/DATA_2TB/administracion-peliculas/downloads -> /downloads
    TORRENT_SEARCH_PATHS = [
        "/downloads/",
        "/downloads/complete/",
        "/downloads/incomplete/",
    ]

    # Rutas legacy (deprecated - ya no se usan)
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

        self._history_service = OptimizationHistoryService()
        self._catalog_service = CatalogUpdateService()
        self._monitor = OptimizationMonitor()
        self._error_handler = OptimizationErrorHandler()

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

    def _add_to_history(
        self,
        process_id: str,
        final_path: str,
        pending: dict,
        status: str = "completed",
        error_message: Optional[str] = None,
    ):
        """
        Añade una entrada al historial de optimizaciones.
        Delega al OptimizationHistoryService.

        IMPORTANTE: Los errores se loguean pero no interrumpen el flujo.
        El error debe ser visible en logs para diagnóstico.
        """
        progress = self._processes.get(process_id)
        logger.info(
            f"[TorrentOptimizer] === GUARDANDO HISTORIAL === process_id={process_id}, status={status}"
        )
        self._history_service.add_entry(
            process_id=process_id,
            final_path=final_path,
            pending=pending,
            status=status,
            error_message=error_message,
            transmission_client=self.transmission_client,
            progress=progress,
        )
        logger.info(
            f"[TorrentOptimizer] ✅ HISTORIAL GUARDADO: process_id={process_id}"
        )

    def _get_cleanup_service(self):
        """Obtiene el servicio de limpieza (inyección de dependencia)"""
        from src.adapters.outgoing.services.cleanup import FileCleanupService

        return FileCleanupService()

    def _find_torrent_file_fallback(
        self, filename: str, torrent_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Busca el archivo en las rutas CORRECTAS (fallback).

        IMPORTANTE: Este método IGNORA el downloadDir de Transmission y busca
        ÚNICAMENTE en las rutas configuradas en TORRENT_SEARCH_PATHS.

        Args:
            filename: Nombre del archivo a buscar (puede incluir o no extensión)
            torrent_id: ID del torrent en Transmission (opcional)

        Returns:
            Ruta completa del archivo si se encuentra, None si no
        """
        search_paths = self.TORRENT_SEARCH_PATHS
        logger.info(
            f"[TorrentOptimizer] Fallback: buscando en rutas correctas: {search_paths}"
        )

        # Extraer nombre base sin extensión
        base_name = filename
        for ext in [
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".webm",
            ".m4v",
            ".wmv",
            ".flv",
            ".ts",
            ".m2ts",
        ]:
            base_name = base_name.replace(ext, "")

        # Intentar con el nombre exacto primero
        for base in search_paths:
            candidate = os.path.join(base, filename)
            logger.info(f"[TorrentOptimizer] Probando: {candidate}")
            if os.path.exists(candidate) and os.path.isfile(candidate):
                logger.info(f"[TorrentOptimizer] ✓ Archivo encontrado: {candidate}")
                return candidate

        # Si no se encuentra, probar con extensiones comunes
        logger.warning(
            f"[TorrentOptimizer] Archivo no encontrado con nombre exacto: {filename}"
        )

        common_extensions = [".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"]
        for base in search_paths:
            for ext in common_extensions:
                # Si el filename ya termina con la extensión, no añadir
                if filename.lower().endswith(ext):
                    continue
                candidate = os.path.join(base, filename + ext)
                if os.path.exists(candidate) and os.path.isfile(candidate):
                    logger.info(
                        f"[TorrentOptimizer] ✓ Archivo encontrado con extensión añadida: {candidate}"
                    )
                    return candidate

        # Búsqueda en subdirectorios
        logger.info(f"[TorrentOptimizer] Buscando en subdirectorios...")
        for base in search_paths:
            if not os.path.exists(base):
                continue
            try:
                for item in os.listdir(base):
                    item_path = os.path.join(base, item)
                    if os.path.isdir(item_path):
                        # Buscar dentro del subdirectorio
                        for file in os.listdir(item_path):
                            if (
                                base_name.lower() in file.lower()
                                and file.lower().endswith(
                                    (".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v")
                                )
                            ):
                                full_path = os.path.join(item_path, file)
                                logger.info(
                                    f"[TorrentOptimizer] ✓ Archivo encontrado en subdirectorio: {full_path}"
                                )
                                return full_path
            except Exception as e:
                logger.warning(f"[TorrentOptimizer] Error listando {base}: {e}")

        # Si aún no se encuentra, listar archivos en las carpetas para debug
        logger.error(
            f"[TorrentOptimizer] ✗ Archivo no encontrado después de probar extensiones"
        )
        for base in search_paths:
            if os.path.exists(base):
                try:
                    files = os.listdir(base)
                    logger.info(
                        f"[TorrentOptimizer] Archivos en {base}: {files[:10]}..."
                    )  # Primeros 10
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
        user_id: Optional[int] = None,
    ) -> str:
        """
        Inicia optimización de un torrent

        Args:
            torrent_id: ID del torrent en Transmission
            category: Categoría para organizar el archivo final
            filename: Nombre del archivo (opcional). Si se proporciona, se usa directamente
                     para buscar en las carpetas de Transmission sin consultar la API
            progress_callback: Función de callback para progreso
            user_id: ID del usuario que inicia la optimización (para historial)

        Returns:
            ID del proceso de optimización

        Raises:
            Exception: Si el archivo no se encuentra
        """
        # Asegurar que tenemos el transmission_client para buscar archivos
        if not self.transmission_client and torrent_id:
            from src.adapters.outgoing.services.transmission import TransmissionClient

            logger.warning(
                "[TorrentOptimizer] Transmission client no configurado, creando uno nuevo"
            )
            self.transmission_client = TransmissionClient()

        # Convertir torrent_id a int si es string
        try:
            torrent_id_int = int(torrent_id) if torrent_id else None
        except (ValueError, TypeError):
            torrent_id_int = None
            logger.warning(f"[TorrentOptimizer] torrent_id inválido: {torrent_id}")

        # Si no se proporciona filename, intentamos obtenerlo de Transmission
        if not filename:
            if not self.transmission_client:
                raise Exception(
                    "Se requiere transmission_client para obtener el nombre del archivo"
                )

            torrent = self.transmission_client.get_torrent(torrent_id_int)
            if not torrent:
                raise FileNotFoundError(
                    f"Torrent {torrent_id_int} no encontrado en Transmission"
                )

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

        # PRIORIZAR: Usar TransmissionClient para obtener la ruta real del archivo
        source_path = None
        if torrent_id_int and self.transmission_client:
            try:
                logger.info(
                    f"[TorrentOptimizer] Intentando obtener ruta desde Transmission (torrent_id={torrent_id_int}, filename={filename})"
                )
                # Intentar obtener la ruta del archivo de video directamente
                source_path = self.transmission_client.get_torrent_file_path(
                    torrent_id_int, filename
                )
                if source_path and os.path.exists(source_path):
                    ext = os.path.splitext(source_path)[1]
                    logger.info(
                        f"[Transmission] ✅ Archivo de entrada encontrado: {source_path} (extensión: {ext})"
                    )
                elif source_path:
                    logger.warning(
                        f"[Transmission] Transmission devolvió ruta pero no existe: {source_path}"
                    )
                else:
                    logger.warning(
                        f"[Transmission] ❌ No se encontró archivo de video para torrent {torrent_id_int}"
                    )
                    # Debug: mostrar información del torrent para diagnosticar
                    debug_info = self.transmission_client.debug_torrent_files(
                        torrent_id_int
                    )
                    logger.warning(
                        f"[Transmission] Debug: download_dir={debug_info.get('download_dir')}, files_count={debug_info.get('files_count')}"
                    )
            except Exception as e:
                logger.warning(
                    f"[TorrentOptimizer] Error usando TransmissionClient: {e}"
                )

        # Fallback: búsqueda tradicional en carpetas solo si falló el método de Transmission
        if not source_path:
            logger.info(
                f"[TorrentOptimizer] Fallback: usando búsqueda tradicional en carpetas para: {filename} (torrent_id={torrent_id_int})"
            )
            source_path = self._find_torrent_file_fallback(filename, torrent_id_int)

        if not source_path:
            raise FileNotFoundError(f"Archivo no encontrado: {filename}")

        # Verificar que source_path es un archivo, no un directorio
        if os.path.isdir(source_path):
            raise FileNotFoundError(
                f"El path encontrado es un directorio, no un archivo: {source_path}"
            )

        # Usar el nombre del archivo real del source_path para generar el nombre de salida
        actual_filename = os.path.basename(source_path)
        logger.info(f"[TorrentOptimizer] Archivo real a procesar: {actual_filename}")

        # Verificar que el archivo existe y es válido ANTES de continuar
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Archivo no encontrado: {source_path}")

        if not os.path.isfile(source_path):
            raise Exception(f"La ruta no es un archivo: {source_path}")

        name_sanitizer = self._get_name_sanitizer()
        # El sanitizador ya añade .mkv, no añadirlo de nuevo
        output_filename = name_sanitizer.sanitize(actual_filename)

        # USAR DIRECTAMENTE la ruta original como input (no copiar)
        # Convertir la ruta del contenedor cine-platform/transmission al contenedor ffmpeg-api
        # cine-platform usa: /downloads/...
        # ffmpeg-api usa: /shared/input/...
        # La transformación es: /downloads/ -> /shared/input/
        # Además, debemos mantener la estructura de subdirectorios que crea Transmission
        shared_input = source_path.replace("/downloads/", "/shared/input/")
        logger.info(
            f"[TorrentOptimizer] Usando archivo original directamente: {shared_input}"
        )
        logger.info(
            f"[TorrentOptimizer] SOURCE es archivo? {os.path.isfile(source_path)}"
        )
        logger.info(f"[TorrentOptimizer] SOURCE existe? {os.path.exists(source_path)}")
        logger.info(
            f"[TorrentOptimizer] SOURCE tamaño: {os.path.getsize(source_path) if os.path.exists(source_path) else 'N/A'}"
        )

        shared_output = os.path.join(SHARED_OUTPUT, output_filename)
        logger.info(
            f"[TorrentOptimizer] Usando archivo de entrada: {shared_input} -> salida: {shared_output}"
        )

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
            torrent_id=torrent_id,  # Guardar torrent_id directamente en el objeto
            category=category,  # Guardar categoría directamente
            original_filename=filename,  # Guardar nombre original
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
            "params": payload[
                "params"
            ],  # Guardar params para reintento si es necesario
            "user_id": user_id,  # ID del usuario que inició la optimización
        }

        # Lanzar el monitoreo INMEDIATAMENTE - no esperar a que la API responda
        # El monitoreoará el estado y esperará hasta que haya un api_process_id
        thread = threading.Thread(
            target=self._monitor_optimization,
            args=(
                process_id,
                None,
                progress_callback,
            ),  # api_process_id puede ser None al inicio
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
                    logger.info(
                        f"[TorrentOptimizer] API process_id recibido: {api_process_id}"
                    )

        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error al llamar a la API: {e}")
            with self._lock:
                progress = self._processes.get(process_id)
                if progress:
                    progress.status = "error"
                    progress.error_message = f"Error al iniciar optimización: {str(e)}"
                    progress.end_time = time.time()

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
                    logger.info(
                        f"[TorrentOptimizer] API process_id obtenido: {current_api_process_id}"
                    )
                    break

            # Verificar si hay un error
            if progress.status == "error":
                logger.warning(
                    f"[TorrentOptimizer] Optimización marcada como error antes de iniciar"
                )
                return

            # Timeout esperando el api_process_id
            if time.time() - wait_start > max_wait_for_api:
                logger.error(f"[TorrentOptimizer] Timeout esperando api_process_id")
                with self._lock:
                    progress.status = "error"
                    progress.error_message = "Timeout esperando respuesta de API"
                    progress.end_time = time.time()
                return

            time.sleep(0.5)  # Esperar 500ms antes de volver a revisar

        # Actualizar estado a running una vez que tenemos el api_process_id
        with self._lock:
            if progress.status == "pending":
                progress.status = "running"
                logger.info(
                    f"[TorrentOptimizer] Estado cambiado a 'running' para {local_process_id}"
                )

        logger.info(
            f"[TorrentOptimizer] Monitoreando proceso: {current_api_process_id}"
        )

        while True:
            try:
                api_status = api_client.get_status(current_api_process_id)

                logger.info(
                    f"[TorrentOptimizer] Estado API para {current_api_process_id}: {api_status}"
                )

                if api_status:
                    # ACTUALIZAR PROGRESO con lock para thread-safety
                    new_progress = api_status.get("progress", 0)
                    new_status = api_status.get("status", "running")

                    with self._lock:
                        # Actualizar solo si hay cambios
                        if new_progress != progress.progress:
                            logger.info(
                                f"[TorrentOptimizer] Progreso actualizado: {progress.progress:.1f}% -> {new_progress:.1f}%"
                            )
                            progress.progress = new_progress

                        if new_status != progress.status:
                            logger.info(
                                f"[TorrentOptimizer] Estado cambiado: {progress.status} -> {new_status}"
                            )
                            progress.status = new_status

                    # Capturar mensaje de error si existe
                    if progress.status == "error":
                        error_msg = api_status.get(
                            "error", "Error desconocido en FFmpeg"
                        )
                        with self._lock:
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
                        with self._lock:
                            progress.logs += "\n".join(logs[-5:]) + "\n"

                    if progress_callback:
                        progress_callback(progress)

                    if progress.status in ["completed", "done"]:
                        with self._lock:
                            progress.end_time = time.time()
                        self._finalize_optimization(local_process_id)
                        break

                time.sleep(int(os.environ.get("OPTIMIZE_POLL_INTERVAL", 2)))

            except Exception as e:
                logger.warning(f"[TorrentOptimizer] Error polling status: {e}")
                time.sleep(5)

    def _finalize_optimization(self, process_id: str):
        """Mueve el archivo optimizado a su destino final y limpia archivos temporales"""
        logger.info(
            f"[TorrentOptimizer] ===== _finalize_optimization() INICIADO para process_id={process_id} ====="
        )

        pending = self._pending.get(process_id)
        if not pending:
            logger.error(
                f"[TorrentOptimizer] ❌ No se encontró metadata para proceso {process_id}"
            )
            return

        try:
            output_path = pending["output_path"]
            category = pending.get("category")
            original_filename = pending["original_filename"]
            shared_input = pending["shared_input"]
            source_path = pending.get("source_path")
            torrent_id = pending.get("torrent_id")
            final_filename = pending.get("final_filename")

            logger.info(f"[TorrentOptimizer] 📋 pending process_id={process_id}:")
            logger.info(f"  - output_path (origen): {output_path}")
            logger.info(f"  - category: {category}")
            logger.info(f"  - original_filename: {original_filename}")
            logger.info(f"  - final_filename: {final_filename}")
            logger.info(f"  - source_path: {source_path}")
            logger.info(f"  - torrent_id: {torrent_id}")
            logger.info(f"  - self.output_folder: {self.output_folder}")

            if not category:
                logger.error(
                    f"[TorrentOptimizer] ❌ Categoría no encontrada en pending para process_id={process_id}"
                )
                return

            # Verificar que el archivo de salida existe antes de proceder
            if not os.path.exists(output_path):
                logger.error(
                    f"[TorrentOptimizer] ❌ Archivo de salida no encontrado: {output_path}. "
                    f"No se realizará la limpieza ni se eliminará el torrent."
                )
                return

            logger.info(
                f"[TorrentOptimizer] ✅ Archivo de salida verificado: {output_path}"
            )

            # Verificar tamaño del archivo
            try:
                file_size = os.path.getsize(output_path)
                logger.info(
                    f"[TorrentOptimizer] 📄 Tamaño del archivo de salida: {file_size} bytes"
                )
            except Exception as e:
                logger.warning(
                    f"[TorrentOptimizer] No se pudo obtener tamaño del archivo: {e}"
                )

            # Construir ruta destino
            category_folder = os.path.join(self.output_folder, category)
            final_path = os.path.join(category_folder, final_filename)

            logger.info(
                f"[TorrentOptimizer] 📁 Carpeta de categoría: {category_folder}"
            )
            logger.info(f"[TorrentOptimizer] 📁 Ruta destino final: {final_path}")

            # Verificar si la carpeta de categoría existe, si no crearla
            if not os.path.exists(category_folder):
                logger.info(
                    f"[TorrentOptimizer] 📂 Creando carpeta de categoría: {category_folder}"
                )
                try:
                    os.makedirs(category_folder, exist_ok=True)
                    logger.info(
                        f"[TorrentOptimizer] ✅ Carpeta de categoría creada: {category_folder}"
                    )
                except Exception as e:
                    logger.error(
                        f"[TorrentOptimizer] ❌ No se pudo crear carpeta de categoría: {e}"
                    )
                    return
            else:
                logger.info(
                    f"[TorrentOptimizer] ✅ Carpeta de categoría ya existe: {category_folder}"
                )

            # Mover el archivo optimizado al catálogo
            try:
                shutil.move(output_path, final_path)
                logger.info(
                    f"[TorrentOptimizer] ✅ Archivo movido a catálogo: {final_path}"
                )
            except PermissionError as e:
                logger.error(
                    f"[TorrentOptimizer] ❌ Error de permisos al mover archivo: {e}"
                )
                return
            except Exception as e:
                logger.error(f"[TorrentOptimizer] ❌ Error al mover archivo: {e}")
                return

            # Añadir al historial de optimizaciones
            self._add_to_history(process_id, final_path, pending, "completed")

            # Actualizar la base de datos del catálogo
            try:
                self._update_catalog_db(final_path, category, pending)
            except Exception as e:
                logger.warning(f"[TorrentOptimizer] ⚠️ Error actualizando catálogo: {e}")

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
            logger.error(
                f"[TorrentOptimizer] ❌ Error finalizando optimización: {e}",
                exc_info=True,
            )

    def _update_catalog_db(self, file_path: str, category: str, metadata: dict):
        """
        Actualiza la base de datos del catálogo con la nueva película optimizada.
        Delega al CatalogUpdateService.
        """
        self._catalog_service.update_catalog(file_path, category, metadata)

    def _handle_error(self, process_id: str, error_message: str):
        """
        Maneja el error de optimización: limpia archivos temporales y registra el error.
        Delega al OptimizationErrorHandler.
        """
        pending = self._pending.get(process_id)
        if not pending:
            logger.error(
                f"[TorrentOptimizer] No se encontró metadata para proceso {process_id}"
            )
            return

        del self._pending[process_id]

        self._error_handler.handle_error(
            process_id=process_id,
            error_message=error_message,
            pending=pending,
            history_service=self._history_service,
        )

    def get_progress(self, process_id: str) -> Optional[OptimizationProgress]:
        """Obtiene el progreso de una optimización (datos locales)"""
        logger.info(f"[TorrentOptimizer] get_progress - Buscando proceso {process_id}")
        with self._lock:
            progress = self._processes.get(process_id)
            if progress:
                # Enriquecer con datos de _pending si están disponibles
                pending = self._pending.get(process_id)
                if pending:
                    progress.torrent_id = pending.get("torrent_id", progress.torrent_id)
                    progress.category = pending.get("category", progress.category)
                    progress.original_filename = pending.get(
                        "original_filename", progress.original_filename
                    )

                logger.info(
                    f"[TorrentOptimizer] get_progress({process_id}): status={progress.status}, progress={progress.progress:.1f}%"
                )
            else:
                logger.warning(
                    f"[TorrentOptimizer] get_progress - Proceso NO encontrado en _processes"
                )
            return progress

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
        # Incluir todos los estados activos
        active_statuses = ["pending", "running", "starting", "copying"]

        logger.info(
            f"[TorrentOptimizer] list_active - Buscando optimizaciones activas (status: {active_statuses})..."
        )
        with self._lock:
            # Debug: mostrar todos los procesos
            logger.info(
                f"[TorrentOptimizer] list_active - Procesos en _processes: {len(self._processes)}"
            )
            logger.info(
                f"[TorrentOptimizer] list_active - Procesos keys: {list(self._processes.keys())}"
            )
            for pid, p in self._processes.items():
                logger.info(
                    f"[TorrentOptimizer] list_active - Proceso {pid}: status='{p.status}'"
                )

            active = []
            for p in self._processes.values():
                # Incluir procesos con status activo
                if p.status in active_statuses:
                    logger.info(
                        f"[TorrentOptimizer] list_active - Incluyendo proceso {p.process_id}: status={p.status}"
                    )

                    # Enrich with metadata from _pending if available
                    pending = self._pending.get(p.process_id)
                    if pending:
                        # Add extra fields for the API response from _pending
                        # Esto asegura que tenemos los datos más recientes
                        p.torrent_id = pending.get("torrent_id", p.torrent_id)
                        p.category = pending.get("category")
                        p.original_filename = pending.get("original_filename")
                    # Si no hay pending, el torrent_id ya debería estar en p (establecido en start_optimization)

                    logger.info(
                        f"[TorrentOptimizer] list_active - proceso {p.process_id}: status={p.status}, torrent_id={getattr(p, 'torrent_id', None)}, category={getattr(p, 'category', None)}"
                    )
                    active.append(p)

            logger.info(
                f"[TorrentOptimizer] list_active - total activos: {len(active)}"
            )
            return active
