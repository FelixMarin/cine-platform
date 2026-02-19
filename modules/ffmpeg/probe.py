# modules/ffmpeg/probe.py
"""
Wrappers para ffprobe.
"""
import os
import subprocess
import json
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


class FFmpegProbe:
    """Wrappers para ffprobe."""
    
    def __init__(self, validator):
        self.validator = validator
    
    def get_video_info(self, video_path: str) -> dict:
        """Obtiene información completa del video."""
        if not self.validator.validate_video_path(video_path):
            logger.error(f"Ruta de video no válida: {video_path}")
            return {}
        
        try:
            cmd = self._build_probe_command(video_path)
            result = self._run_probe_command(cmd, video_path)
            
            if not result:
                return {}
            
            return self._parse_video_info(result, video_path)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout obteniendo info de {video_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error info video: {e}")
            return {}
    
    def _build_probe_command(self, video_path: str) -> list:
        """Construye el comando ffprobe."""
        return [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
    
    def _run_probe_command(self, cmd: list, video_path: str) -> dict:
        """Ejecuta el comando ffprobe."""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Error ffprobe (código {result.returncode}): {result.stderr}")
            return {}
        
        return json.loads(result.stdout)
    
    def _parse_video_info(self, data: dict, video_path: str) -> dict:
        """Parsea la información del video desde el resultado de ffprobe."""
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        v_stream = self._find_stream(streams, "video")
        a_stream = self._find_stream(streams, "audio")
        
        size_mb = self._calculate_size_mb(format_info)
        pix_fmt = v_stream.get("pix_fmt", "").lower() if v_stream else ""
        is_10bit = self._check_10bit(pix_fmt)
        duration = self._parse_duration(format_info)
        
        return {
            "name": os.path.basename(video_path),
            "duration": duration,
            "duration_str": format_info.get("duration", "0"),
            "resolution": self._format_resolution(v_stream),
            "format": format_info.get("format_name", "desconocido"),
            "vcodec": v_stream.get("codec_name", "desconocido") if v_stream else "desconocido",
            "acodec": a_stream.get("codec_name", "desconocido") if a_stream else "desconocido",
            "pix_fmt": pix_fmt,
            "is_10bit": is_10bit,
            "size": f"{size_mb} MB",
            "size_bytes": int(format_info.get("size", 0)) if format_info.get("size") else 0
        }
    
    def _find_stream(self, streams: list, codec_type: str) -> dict:
        """Encuentra el primer stream del tipo especificado."""
        return next((s for s in streams if s.get("codec_type") == codec_type), {})
    
    def _calculate_size_mb(self, format_info: dict) -> float:
        """Calcula el tamaño en MB."""
        size_bytes = int(format_info.get("size", 0)) if format_info.get("size") else 0
        return round(size_bytes / (1024 * 1024), 2) if size_bytes else 0
    
    def _check_10bit(self, pix_fmt: str) -> bool:
        """Verifica si el formato de píxeles es 10-bit."""
        return any(x in pix_fmt for x in ["10", "yuv420p10", "yuv422p10", "yuv444p10"])
    
    def _parse_duration(self, format_info: dict) -> float:
        """Parsea la duración del video."""
        duration_str = format_info.get("duration", "0")
        try:
            return float(duration_str) if duration_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _format_resolution(self, v_stream: dict) -> str:
        """Formatea la resolución del video."""
        if not v_stream:
            return "??x??"
        return f"{v_stream.get('width', '??')}x{v_stream.get('height', '??')}"
    
    def get_duration(self, video_path: str) -> float:
        """Obtiene la duración del video de forma segura."""
        if not self.validator.validate_video_path(video_path):
            logger.error(f"Ruta no válida para obtener duración: {video_path}")
            return 0.0
        
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Error ffprobe en get_duration: {result.stderr}")
                return 0.0
            
            return self._parse_duration_value(result.stdout.strip())
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout obteniendo duración de {video_path}")
            return 0.0
        except Exception as e:
            logger.error(f"Error inesperado en get_duration: {e}")
            return 0.0
    
    def _parse_duration_value(self, duration_str: str) -> float:
        """Parsea el valor de duración."""
        if duration_str:
            try:
                return float(duration_str)
            except ValueError:
                logger.error(f"Error convirtiendo duración a float: '{duration_str}'")
                return 0.0
        return 0.0
