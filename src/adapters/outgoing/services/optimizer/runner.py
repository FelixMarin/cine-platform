"""
Runner de optimización - Ejecuta FFmpeg y captura progreso en tiempo real
"""
import os
import subprocess
import re
import logging
import json
from typing import Optional, Dict
from src.adapters.outgoing.services.optimizer.queue import OptimizationJob, OptimizationQueue

logger = logging.getLogger(__name__)


class FFmpegOutputParser:
    """Parser para el output de FFmpeg"""
    
    # Regex para parsear diferentes métricas
    PATTERNS = {
        'time': re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})'),
        'fps': re.compile(r'fps=\s*(\d+\.?\d*)'),
        'bitrate': re.compile(r'bitrate=\s*(\d+\.?\d*\s*[kmg]?/s)'),
        'size': re.compile(r'size=\s*(\d+\.?\d*\s*[kmg]?B)'),
        'speed': re.compile(r'speed=\s*(\d+\.?\d*x)'),
        'progress': re.compile(r'progress=(\w+)')
    }
    
    @classmethod
    def parse_line(cls, line: str) -> Dict:
        """
        Parsea una línea de output de FFmpeg
        
        Returns:
            Diccionario con las métricas encontradas
        """
        metrics = {}
        
        # Extraer tiempo
        time_match = cls.PATTERNS['time'].search(line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = int(time_match.group(3))
            centiseconds = int(time_match.group(4))
            metrics['time_seconds'] = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        
        # Extraer FPS
        fps_match = cls.PATTERNS['fps'].search(line)
        if fps_match:
            metrics['fps'] = float(fps_match.group(1))
        
        # Extraer bitrate
        bitrate_match = cls.PATTERNS['bitrate'].search(line)
        if bitrate_match:
            metrics['bitrate'] = bitrate_match.group(1)
        
        # Extraer tamaño
        size_match = cls.PATTERNS['size'].search(line)
        if size_match:
            metrics['size_raw'] = size_match.group(1)
            metrics['size_bytes'] = cls._parse_size(size_match.group(1))
        
        # Extraer velocidad
        speed_match = cls.PATTERNS['speed'].search(line)
        if speed_match:
            metrics['speed'] = speed_match.group(1)
        
        return metrics
    
    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Convierte string de tamaño a bytes"""
        size_str = size_str.upper().strip()
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        for unit, multiplier in units.items():
            if unit in size_str:
                try:
                    value = float(size_str.replace(unit, '').strip())
                    return int(value * multiplier)
                except ValueError:
                    return 0
        return 0


class OptimizationRunner:
    """Runner que ejecuta la optimización con FFmpeg"""
    
    def __init__(self, job: OptimizationJob, queue: OptimizationQueue):
        self.job = job
        self.queue = queue
        self.process: Optional[subprocess.Popen] = None
        self._total_duration = 0.0
    
    def run(self):
        """Ejecuta la optimización"""
        logger.info(f"[Optimizer] Starting job: {self.job.id}")
        
        # Verificar que existe el archivo de entrada
        if not os.path.exists(self.job.input_path):
            raise FileNotFoundError(f"Input file not found: {self.job.input_path}")
        
        # Asegurar que existe el directorio de salida
        output_dir = os.path.dirname(self.job.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Obtener duración total del video
        self._total_duration = self._get_duration(self.job.input_path)
        self.job.total_duration = self._total_duration
        
        # Construir comando FFmpeg
        cmd = self._build_ffmpeg_command()
        
        logger.info(f"[Optimizer] FFmpeg command: {' '.join(cmd)}")
        
        # Ejecutar FFmpeg
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Leer output línea a línea
            for line in self.process.stdout:
                if self.job.status.value == 'cancelled':
                    self.process.terminate()
                    break
                
                # Parsear y actualizar progreso
                metrics = FFmpegOutputParser.parse_line(line)
                if metrics:
                    self._update_progress(metrics)
            
            # Esperar a que termine
            self.process.wait()
            
            # Validar resultado
            if self.job.status.value != 'cancelled':
                if self.process.returncode == 0:
                    self._validate_output()
                    self._post_process()
                else:
                    raise RuntimeError(f"FFmpeg exited with code {self.process.returncode}")
                    
        except Exception as e:
            logger.error(f"[Optimizer] Error during optimization: {str(e)}")
            raise
    
    def _get_duration(self, input_path: str) -> float:
        """Obtiene la duración del video usando ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"[Optimizer] Could not get duration: {e}")
        
        return 0.0
    
    def _build_ffmpeg_command(self) -> list:
        """Construye el comando FFmpeg basado en el perfil"""
        from src.adapters.outgoing.services.ffmpeg.encoder import FFmpegEncoderService
        
        # Obtener perfil
        encoder = FFmpegEncoderService()
        profile = encoder.PROFILES.get(self.job.profile, encoder.PROFILES['balanced'])
        
        cmd = [
            'ffmpeg',
            '-i', self.job.input_path,
            '-y',  # Sobrescribir salida
            '-progress', 'pipe:1',  # Output de progreso
        ]
        
        # Video codec
        if profile.get('preset'):
            # Usar NVENC si está disponible
            cmd.extend(['-c:v', 'h264_nvenc'])
            cmd.extend(['-preset', profile['preset']])
        else:
            cmd.extend(['-c:v', 'libx264'])
        
        # Video settings
        if profile.get('quality'):
            cmd.extend(['-crf', str(profile['quality'])])
        
        if profile.get('video_bitrate'):
            cmd.extend(['-b:v', profile['video_bitrate']])
        
        if profile.get('maxrate'):
            cmd.extend(['-maxrate', profile['maxrate']])
        
        if profile.get('bufsize'):
            cmd.extend(['-bufsize', profile['bufsize']])
        
        if profile.get('profile'):
            cmd.extend(['-profile:v', profile['profile']])
        
        # Audio codec
        cmd.extend(['-c:a', 'aac'])
        
        if profile.get('audio_bitrate'):
            cmd.extend(['-b:a', profile['audio_bitrate']])
        
        # Scaling
        if profile.get('scale'):
            cmd.extend(['-vf', f"scale={profile['scale']}"])
        
        # Output
        cmd.append(self.job.output_path)
        
        return cmd
    
    def _update_progress(self, metrics: Dict):
        """Actualiza el progreso del trabajo"""
        current_time = metrics.get('time_seconds', 0)
        
        # Calcular porcentaje
        progress = 0.0
        if self._total_duration > 0:
            progress = (current_time / self._total_duration) * 100
        
        self.queue.update_job_progress(
            self.job.id,
            current_time=current_time,
            progress=progress,
            fps=metrics.get('fps', 0),
            bitrate=self._parse_bitrate(metrics.get('bitrate', '')),
            current_size=metrics.get('size_bytes', 0)
        )
    
    def _parse_bitrate(self, bitrate_str: str) -> int:
        """Convierte bitrate string a bytes"""
        if not bitrate_str:
            return 0
        
        bitrate_str = bitrate_str.strip().lower()
        if 'k' in bitrate_str:
            return int(float(bitrate_str.replace('k/s', '').replace('k', '')) * 1000)
        if 'm' in bitrate_str:
            return int(float(bitrate_str.replace('m/s', '').replace('m', '')) * 1000000)
        return 0
    
    def _validate_output(self):
        """Valida el archivo de salida"""
        logger.info(f"[Optimizer] Validating output: {self.job.output_path}")
        
        if not os.path.exists(self.job.output_path):
            raise FileNotFoundError(f"Output file not created: {self.job.output_path}")
        
        # Verificar duración con ffprobe
        output_duration = self._get_duration(self.job.output_path)
        
        if output_duration > 0 and self._total_duration > 0:
            diff = abs(output_duration - self._total_duration)
            if diff > 1:  # Más de 1 segundo de diferencia
                logger.warning(f"[Optimizer] Duration mismatch: input={self._total_duration}s, output={output_duration}s")
            else:
                logger.info(f"[Optimizer] Validation passed: {output_duration}s")
        
        # Guardar info de archivos
        self.job.files_info = [
            {
                'path': self.job.output_path,
                'size': os.path.getsize(self.job.output_path),
                'duration': output_duration
            }
        ]

    def _post_process(self):
        """
        Ejecuta el post-procesamiento después de la optimización
        """
        logger.info(f"[Optimizer] Starting post-processing for: {self.job.id}")
        
        try:
            from src.adapters.outgoing.services.optimizer.postprocess import process_completed_optimization
            
            job_data = {
                'output_path': self.job.output_path,
                'category': self.job.category,
                'original_filename': os.path.basename(self.job.output_path)
            }
            
            result = process_completed_optimization(self.job.id, job_data)
            
            if result.get('moved'):
                logger.info(f"[Optimizer] Post-processing completed: {result.get('final_path')}")
                # Actualizar la ruta en el trabajo
                self.job.output_path = result.get('final_path', self.job.output_path)
            else:
                logger.warning(f"[Optimizer] Post-processing incomplete: {result.get('errors')}")
                
        except Exception as e:
            logger.error(f"[Optimizer] Post-processing error: {str(e)}")
            # No fallamos la optimización por errores en post-procesamiento
