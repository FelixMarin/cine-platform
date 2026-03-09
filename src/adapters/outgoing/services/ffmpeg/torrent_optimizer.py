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
import re
import logging
import shutil
import threading
import time
import uuid
import requests
from typing import Optional, Dict, Callable, List
from dataclasses import dataclass, field
from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)

# Rutas configurables para el flujo de optimización
# Estas rutas son dentro del contenedor cine-platform
# Transmission descarga a /downloads/ que está montado desde /mnt/DATA_2TB/administracion-peliculas
SHARED_INPUT = os.environ.get("SHARED_INPUT_PATH", "/shared/input")
SHARED_OUTPUT = os.environ.get("SHARED_OUTPUT_PATH", "/shared/outputs")
# Paths where Transmission actually stores files (mounted from host)
TRANSMISSION_COMPLETE = "/mnt/DATA_2TB/administracion-peliculas/complete"
TRANSMISSION_INCOMPLETE = "/mnt/DATA_2TB/administracion-peliculas/incomplete"


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


class TorrentOptimizer:
    """
    Cliente para optimizar archivos de torrent usando FFmpeg API con GPU NVIDIA
    
    Este optimizador maneja el flujo completo:
    - Busca archivos en carpetas de Transmission
    - Copia a zona compartida para FFmpeg API
    - Procesa y mueve resultado a la categoría final
    """

    def __init__(self, upload_folder: str = None, output_folder: str = None, transmission_client=None):
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
        self.api_url = (
            os.environ.get("FFMPEG_API_URL", "http://ffmpeg-api:8080")
            or "http://ffmpeg-api:8080"
        )
        
        # Cliente de Transmission
        self.transmission_client = transmission_client

        self._processes: Dict[str, OptimizationProgress] = {}
        self._pending: Dict[str, Dict] = {}  # Metadata para post-procesamiento
        self._lock = threading.Lock()

        # Crear carpetas necesarias
        os.makedirs(SHARED_INPUT, exist_ok=True)
        os.makedirs(SHARED_OUTPUT, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.temp_folder, exist_ok=True)

        logger.info(f"[TorrentOptimizer] Inicializado. API: {self.api_url}")
        logger.info(f"[TorrentOptimizer] Rutas: SHARED_INPUT={SHARED_INPUT}, SHARED_OUTPUT={SHARED_OUTPUT}")

    def _find_torrent_file(self, torrent) -> Optional[str]:
        """
        Busca el archivo en las posibles ubicaciones de Transmission
        
        IGNORA torrent.download_dir porque apunta a una ruta incorrecta.
        Busca directamente en /downloads/complete/ y /downloads/incomplete/
        
        Args:
            torrent: Objeto TorrentDownload de Transmission
            
        Returns:
            Ruta completa del archivo si se encuentra, None si no
        """
        filename = torrent.name
        logger.info(f"[TorrentOptimizer] Buscando archivo: '{filename}' (repr: {repr(filename)})")
        
        # Rutas a buscar (IGNORAMOS download_dir que es incorrecto)
        possible_paths = []
        
        # 1. /mnt/DATA_2TB/administracion-peliculas/complete/{filename}
        path1 = os.path.join(TRANSMISSION_COMPLETE, filename)
        possible_paths.append(path1)
        logger.info(f"[TorrentOptimizer] Probando: {path1}")
        
        # 2. /mnt/DATA_2TB/administracion-peliculas/incomplete/{filename}
        path2 = os.path.join(TRANSMISSION_INCOMPLETE, filename)
        possible_paths.append(path2)
        logger.info(f"[TorrentOptimizer] Probando: {path2}")
        
        # Buscar en todas las ubicaciones
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"[TorrentOptimizer] ✓ ENCONTRADO: {path}")
                return path
        
        # Si no encuentra, listar archivos en las carpetas para debug
        logger.warning(f"[TorrentOptimizer] Archivo no encontrado: {filename}")
        
        for dir_path in [TRANSMISSION_COMPLETE, TRANSMISSION_INCOMPLETE]:
            logger.warning(f"[TorrentOptimizer] Archivos en {dir_path}:")
            try:
                if os.path.exists(dir_path):
                    for f in os.listdir(dir_path):
                        logger.warning(f"  - {f}")
                else:
                    logger.warning(f"  [DIR NO EXISTE]")
            except Exception as e:
                logger.warning(f"  [ERROR: {e}]")
        
        return None

    def _sanitize_filename(self, filename: str) -> str:
        r"""
        Sanitiza el nombre del archivo para el output
        
        Reglas:
        - Extraer año con regex: r'\(\d{4}\)'
        - Reemplazar espacios y guiones bajos por guiones
        - Eliminar caracteres especiales (solo letras, números, guiones y paréntesis)
        - Convertir a minúsculas
        - Siempre terminar en "-optimized.mkv"
        
        Ejemplos:
        - "Spaceman (2024).mp4" -> "spaceman-(2024)-optimized.mkv"
        - "The Matrix 1999.mkv" -> "the-matrix-(1999)-optimized.mkv"
        - "Inception_2010.avi" -> "inception-(2010)-optimized.mkv"
        
        Args:
            filename: Nombre original del archivo
            
        Returns:
            Nombre sanitizado para el archivo de salida
        """
        # Quitar extensión original
        base_name = os.path.splitext(filename)[0]
        
        # Extraer año si existe
        year_match = re.search(r'\((\d{4})\)', base_name)
        year = year_match.group(1) if year_match else None
        
        # Quitar año del nombre base
        if year:
            base_name = re.sub(r'\s*\(\d{4}\)\s*', '', base_name)
        
        # Reemplazar espacios y guiones bajos por guiones
        base_name = base_name.replace(' ', '-').replace('_', '-')
        
        # Eliminar caracteres especiales (solo letras, números y guiones)
        base_name = re.sub(r'[^a-zA-Z0-9\-]', '', base_name)
        
        # Convertir a minúsculas
        base_name = base_name.lower()
        
        # Eliminar guiones múltiples
        base_name = re.sub(r'-+', '-', base_name)
        
        # Quitar guiones al inicio y final
        base_name = base_name.strip('-')
        
        # Reconstruir nombre con año si existe
        if year:
            final_name = f"{base_name}-({year})-optimized.mkv"
        else:
            final_name = f"{base_name}-optimized.mkv"
        
        logger.info(f"[TorrentOptimizer] Sanitizado: '{filename}' -> '{final_name}'")
        return final_name

    def _copy_to_shared_input(self, source_path: str) -> str:
        """
        Copia el archivo a la carpeta compartida de input para FFmpeg API
        
        Args:
            source_path: Ruta original del archivo
            
        Returns:
            Ruta en /shared/input/
        """
        filename = os.path.basename(source_path)
        shared_input_path = os.path.join(SHARED_INPUT, filename)
        
        # Copiar el archivo (copy2 preserva metadatos)
        shutil.copy2(source_path, shared_input_path)
        logger.info(f"[TorrentOptimizer] Copiado a {shared_input_path}")
        
        return shared_input_path

    def check_gpu_available(self) -> dict:
        """
        Verifica GPU consultando la API de ffmpeg
        
        Returns:
            dict con keys:
                - available (bool): True si hay GPU disponible
                - gpu_name (str): Nombre de la GPU o None
                - error (str): Mensaje de error o None
        """
        try:
            response = requests.get(f"{self.api_url}/gpu-status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                gpu_available = data.get("gpu_available", False)
                gpu_name = data.get("gpu_name") or data.get("gpu_info")
                logger.info(f"[TorrentOptimizer] GPU disponible: {gpu_available}, nombre: {gpu_name}")
                return {
                    "available": gpu_available,
                    "gpu_name": gpu_name,
                    "error": None
                }
            return {"available": False, "gpu_name": None, "error": f"API responded {response.status_code}"}
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"[TorrentOptimizer] No se pudo conectar a la API de FFmpeg: {e}")
            return {"available": False, "gpu_name": None, "error": "No se pudo conectar a la API de FFmpeg"}
        except Exception as e:
            logger.warning(f"[TorrentOptimizer] Error verificando GPU vía API: {e}")
            return {"available": False, "gpu_name": None, "error": str(e)}

    def start_optimization(
        self,
        torrent_id: int,
        category: str,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """
        Inicia optimización de un torrent
        
        Args:
            torrent_id: ID del torrent en Transmission
            category: Categoría para organizar el archivo final
            progress_callback: Función de callback para progreso
            
        Returns:
            ID del proceso de optimización
            
        Raises:
            Exception: Si el torrent no está listo o no se encuentra
        """
        # 1. Obtener torrent desde Transmission
        if not self.transmission_client:
            # Crear cliente si no está configurado
            from src.adapters.outgoing.services.transmission import TransmissionClient
            logger.warning("[TorrentOptimizer] Transmission client no configurado, creando uno nuevo")
            self.transmission_client = TransmissionClient()
        
        torrent = self.transmission_client.get_torrent(torrent_id)
        if not torrent:
            raise Exception(f"Torrent {torrent_id} no encontrado")
        
        logger.info(f"[TorrentOptimizer] Torrent: {torrent.name}, progress={torrent.progress}%")
        
        # 2. Validar progreso REAL
        progress = (torrent.downloaded_ever / torrent.size_when_done) * 100 if torrent.size_when_done > 0 else 0
        if progress < 99.9:
            raise Exception(f"Torrent no completado ({progress:.1f}%)")
        
        # 3. Encontrar archivo en carpetas de Transmission
        source_path = self._find_torrent_file(torrent)
        if not source_path:
            raise Exception(f"Archivo no encontrado: {torrent.name}")
        
        # 4. Sanitizar nombre de salida
        output_filename = self._sanitize_filename(torrent.name)
        
        # 5. Copiar a /shared/input/
        shared_input = os.path.join(SHARED_INPUT, torrent.name)
        shutil.copy2(source_path, shared_input)
        logger.info(f"[TorrentOptimizer] Copiado a {shared_input}")
        
        # 6. Definir ruta de salida en /shared/outputs/
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

        try:
            # 7. Llamar a ffmpeg-api
            response = requests.post(
                f"{self.api_url}/optimize", json=payload, timeout=10
            )

            if response.status_code != 200:
                error_msg = response.json().get("error", "Error desconocido")
                raise RuntimeError(f"Error en API: {error_msg}")

            data = response.json()
            api_process_id = data.get("process_id")

            progress_obj = OptimizationProgress(
                process_id=process_id,
                status="running",
                progress=0.0,
                input_file=source_path,
                output_file=shared_output,
                start_time=time.time(),
            )

            with self._lock:
                self._processes[process_id] = progress_obj
            
            # 8. Guardar metadata para post-procesamiento
            self._pending[process_id] = {
                "output_path": shared_output,
                "category": category,
                "original_filename": torrent.name,
                "final_filename": output_filename,
                "shared_input": shared_input,
            }

            thread = threading.Thread(
                target=self._monitor_optimization,
                args=(process_id, api_process_id, progress_callback),
            )
            thread.daemon = True
            thread.start()

            logger.info(f"[TorrentOptimizer] Optimización iniciada: {process_id}")
            return process_id

        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error starting optimization: {e}")
            # Limpiar archivo copiado en caso de error
            if os.path.exists(shared_input):
                os.remove(shared_input)
            raise

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

        while True:
            try:
                response = requests.get(
                    f"{self.api_url}/status/{api_process_id}", timeout=5
                )

                if response.status_code == 200:
                    data = response.json()

                    progress.status = data.get("status", "running")
                    progress.progress = data.get("progress", 0)

                    logs = data.get("logs", [])
                    if logs:
                        progress.logs += "\n".join(logs[-5:]) + "\n"

                    if progress_callback:
                        progress_callback(progress)

                    if progress.status in ["completed", "error"]:
                        if progress.status == "completed":
                            progress.end_time = time.time()
                            self._finalize_optimization(local_process_id)
                        break

                time.sleep(2)

            except Exception as e:
                logger.warning(f"[TorrentOptimizer] Error polling status: {e}")
                time.sleep(5)

    def _finalize_optimization(self, process_id: str):
        """
        Mueve el archivo optimizado a su destino final y limpia archivos temporales
        
        Args:
            process_id: ID del proceso de optimización
        """
        pending = self._pending.get(process_id)
        if not pending:
            logger.error(f"[TorrentOptimizer] No se encontró metadata para proceso {process_id}")
            return
        
        try:
            output_path = pending["output_path"]
            category = pending["category"]
            original_filename = pending["original_filename"]
            shared_input = pending["shared_input"]
            
            # Construir ruta final
            final_path = os.path.join(self.output_folder, category, pending["final_filename"])
            
            # Asegurar directorio existe
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Mover archivo optimizado a su destino final
            shutil.move(output_path, final_path)
            logger.info(f"[TorrentOptimizer] Archivo movido a: {final_path}")
            
            # Limpiar archivo temporal de input en /shared/input/
            if os.path.exists(shared_input):
                os.remove(shared_input)
                logger.info(f"[TorrentOptimizer] Limpiado archivo temporal: {shared_input}")
            
            # Limpiar de _pending
            del self._pending[process_id]
            
        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error finalizando optimización: {e}")

    def get_progress(self, process_id: str) -> Optional[OptimizationProgress]:
        """Obtiene el progreso de una optimización (datos locales)"""
        with self._lock:
            return self._processes.get(process_id)

    def cancel_optimization(self, process_id: str) -> bool:
        """Cancela una optimización en curso"""
        logger.warning(
            f"[TorrentOptimizer] Cancelación no implementada para {process_id}"
        )
        return False

    def list_active(self) -> List[OptimizationProgress]:
        """Lista todas las optimizaciones activas"""
        with self._lock:
            return [p for p in self._processes.values() if p.status == "running"]
