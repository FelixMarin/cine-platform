# modules/ffmpeg/validator.py
"""
Validación de rutas y argumentos FFmpeg.
"""
import os
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


class FFmpegValidator:
    """Validación de rutas de video y argumentos de comandos."""
    
    def __init__(self, config):
        self.config = config
    
    def validate_video_path(self, video_path: str) -> bool:
        """Valida que la ruta del video sea segura."""
        if not video_path or not isinstance(video_path, str):
            return False
        
        # Prevenir path traversal
        if '..' in video_path or video_path.startswith('/'):
            return self._is_path_in_allowed_dirs(video_path)
        
        return True
    
    def _is_path_in_allowed_dirs(self, video_path: str) -> bool:
        """Verifica si la ruta está en directorios permitidos."""
        import os
        abs_path = os.path.abspath(video_path)
        for allowed in self.config.get_allowed_dirs():
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        return False
    
    def validate_command_args(self, cmd_args: list) -> bool:
        """Valida que los argumentos del comando sean seguros."""
        if not isinstance(cmd_args, list):
            logger.error("cmd_args debe ser una lista")
            return False
        
        for arg in cmd_args:
            if not isinstance(arg, str):
                logger.error(f"Argumento no válido: {arg}")
                return False
        
        return True
    
    def build_command_string(self, cmd_args: list) -> str:
        """Construye una cadena de comando para logging."""
        return ' '.join(str(arg) for arg in cmd_args)
