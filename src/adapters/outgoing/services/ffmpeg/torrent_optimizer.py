"""
Cliente de optimización de torrents usando FFmpeg

Este servicio proporciona métodos para optimizar archivos de video descargados
usando FFmpeg con aceleración GPU NVIDIA.
"""
import os
import subprocess
import logging
import threading
import time
import signal
from typing import Optional, Dict, Any, Callable
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
    Cliente para optimizar archivos de torrent usando FFmpeg con NVIDIA GPU
    """
    
    # Comando FFmpeg fijo para optimización
    FFMPEG_COMMAND = [
        "ffmpeg",
        "-hwaccel", "cuda",
        "-i", "{input_path}",
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
        "{output_path}"
    ]
    
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
        
        logger.info(f"[TorrentOptimizer] Inicializado. Upload: {self.upload_folder}, Output: {self.output_folder}")
    
    def check_gpu_available(self) -> bool:
        """
        Verifica si hay GPU NVIDIA disponible
        
        Returns:
            True si hay GPU disponible
        """
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=5
            )
            available = result.returncode == 0
            logger.info(f"[TorrentOptimizer] GPU NVIDIA disponible: {available}")
            return available
        except Exception as e:
            logger.warning(f"[TorrentOptimizer] Error verificando GPU: {e}")
            return False
    
    def _build_command(self, input_path: str, output_path: str) -> list:
        """
        Construye el comando FFmpeg con las rutas especificadas
        
        Args:
            input_path: Ruta del archivo de entrada
            output_path: Ruta del archivo de salida
            
        Returns:
            Lista de argumentos para subprocess
        """
        cmd = []
        for part in self.FFMPEG_COMMAND:
            if part == "{input_path}":
                cmd.append(input_path)
            elif part == "{output_path}":
                cmd.append(output_path)
            else:
                cmd.append(part)
        return cmd
    
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
        
        # Carpeta según categoría
        category_folder = os.path.join(self.output_folder, category)
        os.makedirs(category_folder, exist_ok=True)
        
        output_path = os.path.join(category_folder, output_filename)
        return output_path
    
    def start_optimization(
        self,
        input_path: str,
        category: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Inicia la optimización de un archivo
        
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
        
        # Determinar ruta de salida
        output_path = self._determine_output_path(input_filename, category)
        
        # Verificar GPU
        if not self.check_gpu_available():
            logger.warning("[TorrentOptimizer] GPU no disponible, usando CPU")
        
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
            args=(process_id, input_path, output_path, progress_callback)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"[TorrentOptimizer] Started optimization {process_id}: {input_path} -> {output_path}")
        return process_id
    
    def _run_ffmpeg(
        self,
        process_id: str,
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Ejecuta FFmpeg en un hilo separado
        """
        progress = self._processes.get(process_id)
        if not progress:
            return
        
        try:
            # Construir comando
            cmd = self._build_command(input_path, output_path)
            cmd_str = ' '.join(cmd)
            
            logger.info(f"[TorrentOptimizer] Ejecutando comando: {cmd_str}")
            progress.logs += f"[{time.strftime('%H:%M:%S')}] Iniciando optimización...\n"
            progress.logs += f"[{time.strftime('%H:%M:%S')}] Comando: {cmd_str}\n"
            
            # Obtener duración total del video
            duration = self._get_video_duration(input_path)
            if duration:
                progress.logs += f"[{time.strftime('%H:%M:%S')}] Duración total: {duration:.2f}s\n"
            
            # Ejecutar FFmpeg
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
    
    def _get_video_duration(self, input_path: str) -> Optional[float]:
        """
        Obtiene la duración del video usando ffprobe
        
        Args:
            input_path: Ruta del video
            
        Returns:
            Duración en segundos o None
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    input_path
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"[TorrentOptimizer] Error obteniendo duración: {e}")
        return None
    
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
        # Por ahora retorna False
        logger.warning(f"[TorrentOptimizer] Cancelación no implementada para {process_id}")
        return False
    
    def list_active(self) -> list:
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
