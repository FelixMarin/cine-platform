"""
Cliente de optimización de torrents usando FFmpeg en contenedor Docker

Este servicio proporciona métodos para optimizar archivos de video descargados
usando FFmpeg con aceleración GPU NVIDIA en un contenedor separado.
"""
import os
import subprocess
import logging
import threading
import time
import signal
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)


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
    Cliente para optimizar archivos de torrent usando FFmpeg en contenedor Docker con GPU NVIDIA
    """
    
    # Configuración del contenedor FFmpeg
    FFMPEG_CONTAINER = "ffmpeg-cuda"
    SHARED_INPUT = "/shared/input"
    SHARED_OUTPUT = "/shared/output"
    SHARED_TEMP = "/shared/temp"
    
    # Comando base para ejecutar en contenedor
    DOCKER_EXEC = ["docker", "exec", FFMPEG_CONTAINER]
    
    def __init__(self, upload_folder: str = None, output_folder: str = None):
        """
        Inicializa el optimizador de torrents
        
        Args:
            upload_folder: Carpeta donde están los archivos descargados
            output_folder: Carpeta donde se guardarán los archivos optimizados
        """
        self.upload_folder = upload_folder or settings.UPLOAD_FOLDER
        self.output_folder = output_folder or settings.MOVIES_BASE_PATH
        self.temp_folder = '/tmp/cineplatform/temp'
        
        # Procesos activos
        self._processes: Dict[str, OptimizationProgress] = {}
        self._lock = threading.Lock()
        
        # Crear carpetas si no existen
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.temp_folder, exist_ok=True)
        
        # Verificar que el contenedor está corriendo
        self._check_container()
        
        logger.info(f"[TorrentOptimizer] Inicializado. Upload: {self.upload_folder}, Output: {self.output_folder}")
    
    def _check_container(self) -> bool:
        """
        Verifica que el contenedor FFmpeg está corriendo
        
        Returns:
            True si el contenedor está corriendo
            
        Raises:
            RuntimeError: Si el contenedor no está disponible
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.FFMPEG_CONTAINER}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if self.FFMPEG_CONTAINER in result.stdout:
                logger.info(f"[TorrentOptimizer] ✅ Contenedor {self.FFMPEG_CONTAINER} disponible")
                return True
            else:
                error_msg = f"❌ Contenedor {self.FFMPEG_CONTAINER} no está corriendo"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"❌ Error verificando contenedor {self.FFMPEG_CONTAINER}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _map_to_container_path(self, local_path: str) -> str:
        """
        Convierte una ruta local a su equivalente en el contenedor
        
        Args:
            local_path: Ruta en el host
            
        Returns:
            Ruta equivalente en el contenedor
        """
        # Mapear rutas según los volúmenes definidos en docker-compose
        if self.upload_folder in local_path:
            return local_path.replace(self.upload_folder, self.SHARED_INPUT)
        elif self.output_folder in local_path:
            # Para archivos de salida, usar la carpeta temp primero
            filename = os.path.basename(local_path)
            return f"{self.SHARED_TEMP}/{filename}"
        elif self.temp_folder in local_path:
            return local_path.replace(self.temp_folder, self.SHARED_TEMP)
        elif "/mnt/DATA_2TB/audiovisual/mkv" in local_path:
            return local_path.replace("/mnt/DATA_2TB/audiovisual/mkv", self.SHARED_OUTPUT)
        else:
            # Fallback: asumir que está en temp
            filename = os.path.basename(local_path)
            return f"{self.SHARED_TEMP}/{filename}"
    
    def _map_from_container_path(self, container_path: str) -> str:
        """
        Convierte una ruta del contenedor a su equivalente local
        
        Args:
            container_path: Ruta en el contenedor
            
        Returns:
            Ruta equivalente en el host
        """
        if container_path.startswith(self.SHARED_INPUT):
            return container_path.replace(self.SHARED_INPUT, self.upload_folder)
        elif container_path.startswith(self.SHARED_OUTPUT):
            return container_path.replace(self.SHARED_OUTPUT, self.output_folder)
        elif container_path.startswith(self.SHARED_TEMP):
            return container_path.replace(self.SHARED_TEMP, self.temp_folder)
        return container_path
    
    def check_gpu_available(self) -> bool:
        """
        Verifica si hay GPU NVIDIA disponible en el contenedor
        
        Returns:
            True si hay GPU disponible
        """
        try:
            cmd = self.DOCKER_EXEC + ["nvidia-smi"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            available = result.returncode == 0
            logger.info(f"[TorrentOptimizer] GPU NVIDIA disponible en contenedor: {available}")
            return available
        except Exception as e:
            logger.warning(f"[TorrentOptimizer] Error verificando GPU: {e}")
            return False
    
    def _determine_output_path(self, input_filename: str, category: str) -> str:
        """
        Determina la ruta de salida según la categoría
        
        Args:
            input_filename: Nombre del archivo de entrada
            category: Categoría (action, drama, sci_fi, etc.)
            
        Returns:
            Ruta completa del archivo de salida
        """
        # Quitar extensión
        base_name = os.path.splitext(input_filename)[0]
        output_filename = f"{base_name}-optimized.mkv"
        
        # Primero va a temp, luego se moverá a la categoría final
        output_path = os.path.join(self.temp_folder, output_filename)
        return output_path
    
    def _get_video_duration(self, input_path: str) -> Optional[float]:
        """
        Obtiene la duración del video usando ffprobe en el contenedor
        
        Args:
            input_path: Ruta del video
            
        Returns:
            Duración en segundos o None
        """
        try:
            container_path = self._map_to_container_path(input_path)
            cmd = self.DOCKER_EXEC + [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                container_path
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"[TorrentOptimizer] Error obteniendo duración: {e}")
        return None
    
    def start_optimization(
        self,
        input_path: str,
        category: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Inicia la optimización de un archivo usando el contenedor FFmpeg
        
        Args:
            input_path: Ruta completa del archivo a optimizar
            category: Categoría para organizar el archivo
            progress_callback: Función para recibir actualizaciones de progreso
            
        Returns:
            ID del proceso de optimización
        """
        import uuid
        
        # Validar archivo de entrada
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Archivo no encontrado: {input_path}")
        
        input_filename = os.path.basename(input_path)
        
        # Determinar ruta de salida temporal
        output_path = self._determine_output_path(input_filename, category)
        
        # Convertir rutas a paths del contenedor
        container_input = self._map_to_container_path(input_path)
        container_output = self._map_to_container_path(output_path)
        
        # Verificar GPU (opcional, no crítico)
        self.check_gpu_available()
        
        # Generar ID único
        process_id = str(uuid.uuid4())
        
        # Crear objeto de progreso
        progress = OptimizationProgress(
            process_id=process_id,
            status='running',
            progress=0.0,
            input_file=input_path,
            output_file=output_path,
            start_time=time.time()
        )
        
        with self._lock:
            self._processes[process_id] = progress
        
        # Iniciar proceso en hilo separado
        thread = threading.Thread(
            target=self._run_ffmpeg,
            args=(process_id, container_input, container_output, input_path, output_path, category, progress_callback)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"[TorrentOptimizer] Started optimization {process_id}: {input_path} -> {output_path}")
        return process_id
    
    def _run_ffmpeg(
        self,
        process_id: str,
        container_input: str,
        container_output: str,
        local_input: str,
        local_output: str,
        category: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Ejecuta FFmpeg en el contenedor en un hilo separado
        """
        progress = self._processes.get(process_id)
        if not progress:
            return
        
        try:
            # Obtener duración para calcular progreso
            duration = self._get_video_duration(local_input)
            if duration:
                progress.logs += f"[{time.strftime('%H:%M:%S')}] Duración total: {duration:.2f}s\n"
            
            # Construir comando para ejecutar en contenedor
            cmd = self.DOCKER_EXEC + [
                "ffmpeg",
                "-hwaccel", "cuda",
                "-i", container_input,
                "-c:v", "h264_nvenc",
                "-preset", "p7",
                "-rc", "vbr",
                "-tune", "hq",
                "-multipass", "fullres",
                "-cq", "28",
                "-b:v", "1800k",
                "-maxrate", "2200k",
                "-bufsize", "4400k",
                "-rc-lookahead", "32",
                "-profile:v", "high",
                "-level", "4.1",
                "-pix_fmt", "yuv420p",
                "-g", "120",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
                "-ar", "48000",
                "-c:s", "copy",
                "-f", "matroska",
                "-y",
                container_output
            ]
            
            cmd_str = ' '.join(cmd)
            logger.info(f"[TorrentOptimizer] Ejecutando en contenedor: {cmd_str}")
            progress.logs += f"[{time.strftime('%H:%M:%S')}] Iniciando optimización en contenedor...\n"
            progress.logs += f"[{time.strftime('%H:%M:%S')}] Comando: {cmd_str}\n"
            
            # Ejecutar FFmpeg en el contenedor
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitorear progreso
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    progress.logs += line
                    
                    # Extraer progreso del tiempo
                    if duration and 'time=' in line:
                        try:
                            time_str = line.split('time=')[1].split()[0]
                            parts = time_str.split(':')
                            if len(parts) == 3:
                                current_time = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                                progress.progress = min(100, (current_time / duration) * 100)
                                
                                if progress_callback:
                                    progress_callback(progress)
                        except:
                            pass
            
            # Obtener código de salida
            return_code = process.wait()
            
            if return_code == 0:
                progress.status = 'done'
                progress.progress = 100.0
                progress.end_time = time.time()
                elapsed = progress.end_time - progress.start_time
                progress.logs += f"[{time.strftime('%H:%M:%S')}] ✅ Optimización completada en {elapsed:.1f}s\n"
                
                # Mover el archivo de temp a la carpeta final de categoría
                self._move_to_category(local_output, progress.input_file, category)
                
                logger.info(f"[TorrentOptimizer] Optimización {process_id} completada")
            else:
                progress.status = 'error'
                progress.end_time = time.time()
                progress.error_message = f"FFmpeg terminó con código {return_code}"
                progress.logs += f"[{time.strftime('%H:%M:%S')}] ❌ Error: {progress.error_message}\n"
                logger.error(f"[TorrentOptimizer] Error en optimización {process_id}: {progress.error_message}")
            
            if progress_callback:
                progress_callback(progress)
                
        except Exception as e:
            progress.status = 'error'
            progress.error_message = str(e)
            progress.end_time = time.time()
            progress.logs += f"[{time.strftime('%H:%M:%S')}] ❌ Excepción: {str(e)}\n"
            logger.error(f"[TorrentOptimizer] Excepción en optimización {process_id}: {e}")
            
            if progress_callback:
                progress_callback(progress)
    
    def _move_to_category(self, temp_path: str, input_path: str, category: str):
        """
        Mueve el archivo optimizado de temp a la carpeta de categoría
        
        Args:
            temp_path: Ruta temporal del archivo optimizado
            input_path: Ruta del archivo original (para extraer nombre)
            category: Categoría destino
        """
        try:
            # Extraer nombre base del archivo original
            input_filename = os.path.basename(input_path)
            base_name = os.path.splitext(input_filename)[0]
            
            # Crear nombre final (normalizado)
            final_filename = f"{base_name.replace(' ', '-')}-optimized.mkv"
            
            # Carpeta destino por categoría
            category_folder = os.path.join(self.output_folder, category)
            os.makedirs(category_folder, exist_ok=True)
            
            final_path = os.path.join(category_folder, final_filename)
            
            # Mover archivo
            import shutil
            shutil.move(temp_path, final_path)
            
            logger.info(f"[TorrentOptimizer] Archivo movido a: {final_path}")
            
        except Exception as e:
            logger.error(f"[TorrentOptimizer] Error moviendo archivo a categoría: {e}")
    
    def get_progress(self, process_id: str) -> Optional[OptimizationProgress]:
        """
        Obtiene el progreso de una optimización
        
        Args:
            process_id: ID del proceso
            
        Returns:
            Objeto OptimizationProgress o None
        """
        with self._lock:
            return self._processes.get(process_id)
    
    def cancel_optimization(self, process_id: str) -> bool:
        """
        Cancela una optimización en curso
        
        Args:
            process_id: ID del proceso
            
        Returns:
            True si se canceló correctamente
        """
        # Esta funcionalidad requeriría mantener referencia al proceso
        logger.warning(f"[TorrentOptimizer] Cancelación no implementada para {process_id}")
        return False
    
    def list_active(self) -> List[OptimizationProgress]:
        """
        Lista todas las optimizaciones activas
        
        Returns:
            Lista de procesos activos
        """
        with self._lock:
            return [
                p for p in self._processes.values()
                if p.status == 'running'
            ]