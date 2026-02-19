# modules/ffmpeg/config.py
"""
Configuración y detección de hardware FFmpeg.
"""
import os
import subprocess
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


class FFmpegConfig:
    """Manejo de configuración y detección de hardware FFmpeg."""
    
    # Directorios permitidos para rutas absolutas
    ALLOWED_DIRS = [
        '/data/media',
        '/tmp/uploads',
        '/tmp/temp',
        '/tmp/outputs',
        '/app/uploads',
        '/app/temp',
        '/app/outputs'
    ]
    
    def __init__(self):
        self.is_jetson = self._detect_jetson()
        self.has_nvmpi_h264 = False
        self.has_nvmpi_hevc = False
        self.has_nvmpi_vp9 = False
        
        if self.is_jetson:
            logger.info("✅ Dispositivo Jetson detectado")
            self._check_nvmpi_decoders()
    
    def _detect_jetson(self) -> bool:
        """Detecta si el dispositivo es un Jetson."""
        return os.path.exists("/usr/lib/aarch64-linux-gnu/tegra")
    
    def _check_nvmpi_decoders(self):
        """Verifica qué decodificadores NVMPI están disponibles."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-decoders"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            decoders = result.stdout
            
            self.has_nvmpi_h264 = "h264_nvmpi" in decoders
            self.has_nvmpi_hevc = "hevc_nvmpi" in decoders
            self.has_nvmpi_vp9 = "vp9_nvmpi" in decoders
            
            logger.info(f"📊 Decodificadores NVMPI: H264={self.has_nvmpi_h264}, HEVC={self.has_nvmpi_hevc}, VP9={self.has_nvmpi_vp9}")
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout verificando decodificadores")
            self._set_decoders_false()
        except Exception as e:
            logger.error(f"Error verificando decodificadores: {e}")
            self._set_decoders_false()
    
    def _set_decoders_false(self):
        """Establece todos los decodificadores a False."""
        self.has_nvmpi_h264 = False
        self.has_nvmpi_hevc = False
        self.has_nvmpi_vp9 = False
    
    def get_allowed_dirs(self) -> list:
        """Retorna la lista de directorios permitidos."""
        return self.ALLOWED_DIRS.copy()
