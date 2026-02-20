# modules/ffmpeg/process.py
"""
Manejo de ejecución y limpieza de procesos FFmpeg.
"""
import os
import subprocess
import signal
import re
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


class FFmpegProcess:
    """Manejo de ejecución y limpieza de procesos FFmpeg."""
    
    def __init__(self):
        self.current_process = None
        self.set_process_callback = None
        
        # Compilar patrones regex una sola vez
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compila los patrones regex para extracción de progreso."""
        self.frame_pattern = re.compile(r'frame=\s*(\d+)')
        self.fps_pattern = re.compile(r'fps=\s*([\d.]+)')
        self.time_pattern = re.compile(r'time=\s*([\d:]+)')
        self.bitrate_pattern = re.compile(r'bitrate=\s*([\d.]+)kbits/s')
        self.speed_pattern = re.compile(r'speed=\s*([\d.]+)x')
    
    def set_callback(self, callback):
        """Establece el callback para el proceso."""
        self.set_process_callback = callback
    
    def execute(self, cmd_args: list, state_manager=None) -> bool:
        """Ejecuta un comando FFmpeg de forma segura."""
        if not isinstance(cmd_args, list):
            logger.error("cmd_args debe ser una lista")
            return False
        
        # Validar argumentos
        for arg in cmd_args:
            if not isinstance(arg, str):
                logger.error(f"Argumento no válido: {arg}")
                return False
        
        logger.debug(f"CMD: {' '.join(str(arg) for arg in cmd_args)}")
        
        process = None
        try:
            process = self._start_process(cmd_args)
            self.current_process = process
            
            if self.set_process_callback:
                self.set_process_callback(process)
            
            # Procesar salida del proceso
            self._process_output(process, state_manager)
            
            return self._check_process_result(process)
            
        except Exception as e:
            logger.error(f"❌ Error en execute: {e}")
            return False
        finally:
            self._cleanup_after_execution(process)
    
    def _start_process(self, cmd_args: list) -> subprocess.Popen:
        """Inicia el proceso FFmpeg."""
        return subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
    
    def _process_output(self, process, state_manager):
        """Procesa la salida del proceso extrayendo información de progreso."""
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.debug(line)
                self._extract_progress(line, state_manager)
    
    def _extract_progress(self, line: str, state_manager):
        """Extrae información de progreso de la línea de salida."""
        if "frame=" not in line and "fps=" not in line:
            return
        
        stats_parts = []
        
        # Extraer frame
        frame_match = self.frame_pattern.search(line)
        if frame_match:
            stats_parts.append(f"frames={frame_match.group(1)}")
        
        # Extraer FPS
        fps_match = self.fps_pattern.search(line)
        if fps_match:
            stats_parts.append(f"fps={fps_match.group(1)}")
        
        # Extraer tiempo
        time_match = self.time_pattern.search(line)
        if time_match:
            stats_parts.append(f"time={time_match.group(1)}")
        
        # Extraer bitrate
        bitrate_match = self.bitrate_pattern.search(line)
        if bitrate_match:
            stats_parts.append(f"bitrate={bitrate_match.group(1)}k")
        
        # Extraer speed
        speed_match = self.speed_pattern.search(line)
        if speed_match:
            stats_parts.append(f"speed={speed_match.group(1)}x")
        
        if stats_parts and state_manager:
            log_line = " | ".join(stats_parts)
            if hasattr(state_manager, 'update_log'):
                state_manager.update_log(log_line)
    
    def _check_process_result(self, process) -> bool:
        """Verifica el resultado del proceso."""
        process.wait()
        
        if process.returncode != 0:
            logger.error(f"❌ FFmpeg error code: {process.returncode}")
            return False
        
        return True
    
    def _cleanup_after_execution(self, process):
        """Limpia después de la ejecución."""
        self.current_process = None
        if self.set_process_callback:
            self.set_process_callback(None)
        self._cleanup_process(process)
    
    def _cleanup_process(self, process):
        """Limpia el proceso de forma segura."""
        if not process or process.poll() is not None:
            return
        
        try:
            if hasattr(os, 'killpg') and hasattr(process, 'pid'):
                self._terminate_with_pgid(process)
            else:
                self._terminate_simple(process)
        except Exception as e:
            logger.error(f"Error limpiando proceso: {e}")
    
    def _terminate_with_pgid(self, process):
        """Termina el proceso usando killpg."""
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            self._force_kill_with_pgid(process)
    
    def _terminate_simple(self, process):
        """Termina el proceso de forma simple."""
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    def _force_kill_with_pgid(self, process):
        """Fuerza la eliminación del proceso."""
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    
    def cancel_current_process(self) -> bool:
        """Cancela el proceso actual."""
        if not self.current_process or self.current_process.poll() is not None:
            return False
        
        try:
            logger.info("🛑 Cancelando proceso FFmpeg...")
            if hasattr(os, 'killpg') and hasattr(self.current_process, 'pid'):
                os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
            else:
                self.current_process.terminate()
            return True
        except Exception as e:
            logger.error(f"Error cancelando proceso: {e}")
            return False
