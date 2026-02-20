# Funciones auxiliares para ffmpeg/ffprobe

import subprocess
import magic
import os
from modules.media.constants import (
    PROCESSING_TIMEOUT,
    FFPROBE_TIMEOUT,
    FFPROBE_TIMEOUT_LONG,
    THUMBNAIL_DEFAULT_CAPTURE_TIME,
    THUMBNAIL_CAPTURE_PERCENT,
    THUMBNAIL_MIN_DURATION_FOR_PERCENT,
    THUMBNAIL_DEFAULT_SIZE,
    THUMBNAIL_DEFAULT_QUALITY,
    THUMBNAIL_WEBP_QUALITY,
    THUMBNAIL_WEBP_COMPRESSION
)
from modules.media.utils import sanitize_for_log
from modules.logging.logging_config import setup_logging
import os as os_env

logger = setup_logging(os_env.environ.get("LOG_FOLDER"))


def check_mime_type(video_path):
    """Valida que el archivo sea un video basado en su tipo MIME"""
    try:
        mime = magic.from_file(video_path, mime=True)
        if not mime.startswith('video/'):
            logger.error(f"Archivo no es video: {mime}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error validando MIME: {e}")
        return False


def check_ffmpeg_webp_support():
    """Verifica si ffmpeg soporta WebP"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        return "libwebp" in result.stdout
    except:
        return False


def get_video_duration(video_path, is_path_safe_func=None):
    """Obtiene la duración del video en segundos usando ffprobe"""
    # Validar MIME type primero
    if not check_mime_type(video_path):
        return None

    # Verificar que la ruta es segura si se proporciona la función
    if is_path_safe_func and not is_path_safe_func(video_path):
        logger.error(f"Ruta no permitida para obtener duración: {video_path}")
        return None
    
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=FFPROBE_TIMEOUT_LONG,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Error en ffprobe: {result.stderr}")
            return None
            
        duration = float(result.stdout.strip())
        return duration
    except ValueError:
        logger.error(f"Error convirtiendo duración a float: {result.stdout}")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout obteniendo duración de {video_path}")
        return None
    except Exception as e:
        logger.error(f"Error obteniendo duración: {e}")
        return None


def calculate_capture_time(duration):
    """Calcula el tiempo óptimo para capturar el thumbnail"""
    if duration and duration > THUMBNAIL_MIN_DURATION_FOR_PERCENT:
        capture_time = min(120, int(duration * THUMBNAIL_CAPTURE_PERCENT))
    else:
        capture_time = THUMBNAIL_DEFAULT_CAPTURE_TIME
    
    hours = capture_time // 3600
    minutes = (capture_time % 3600) // 60
    seconds = capture_time % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def generate_thumbnail(video_path, thumbnail_path, is_path_safe_func=None):
    """Genera un thumbnail en la ruta especificada"""
    try:
        # Verificar que el video existe
        if not os.path.exists(video_path):
            logger.error(f"Video no encontrado: {video_path}")
            return False
        
        # Verificar que la ruta del thumbnail está dentro de la carpeta permitida
        if is_path_safe_func and not is_path_safe_func(video_path):
            logger.error(f"Ruta de video no permitida: {video_path}")
            return False
        
        # Obtener duración del video
        duration = get_video_duration(video_path)
        time_str = calculate_capture_time(duration)
        
        use_webp = thumbnail_path.endswith('.webp')
        
        # Construcción del comando ffmpeg
        base_cmd = [
            "ffmpeg", 
            "-y",
            "-i", video_path,
            "-ss", time_str,
            "-vframes", "1",
            "-vf", f"scale={THUMBNAIL_DEFAULT_SIZE}:-1",
        ]
        
        if use_webp:
            cmd = base_cmd + [
                "-c:v", "libwebp",
                "-lossless", "0",
                "-compression_level", str(THUMBNAIL_WEBP_COMPRESSION),
                "-q:v", str(THUMBNAIL_WEBP_QUALITY),
                "-preset", "picture",
                thumbnail_path
            ]
        else:
            cmd = base_cmd + [
                "-q:v", str(THUMBNAIL_DEFAULT_QUALITY),
                "-pix_fmt", "yuvj420p",
                thumbnail_path
            ]
        
        # Ejecutar con timeout
        result = subprocess.run(
            cmd, 
            check=True,
            text=True,
            timeout=PROCESSING_TIMEOUT,
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout generando thumbnail para {video_path}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ffmpeg para {video_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return False
