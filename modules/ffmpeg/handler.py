# modules/ffmpeg/handler.py
"""
Clase principal que coordina las operaciones de FFmpeg.
"""
from .config import FFmpegConfig
from .validator import FFmpegValidator
from .probe import FFmpegProbe
from .process import FFmpegProcess


class FFmpegHandler:
    """
    Clase principal que coordina las operaciones de FFmpeg.
    Delega las responsabilidades a clases especializadas.
    """
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
        
        # Inicializar clases especializadas
        self.config = FFmpegConfig()
        self.validator = FFmpegValidator(self.config)
        self.probe = FFmpegProbe(self.validator)
        self.process = FFmpegProcess()
        
        # Conectar callback del proceso
        self.process.set_callback(self._on_process_update)
    
    def _on_process_update(self, process):
        """Callback para actualizaciones del proceso."""
        # Este callback puede extenderse para más funcionalidad
        pass
    
    # -------------------------------------------------------------------------
    # Métodos de configuración
    # -------------------------------------------------------------------------
    
    @property
    def is_jetson(self) -> bool:
        """Retorna si es un dispositivo Jetson."""
        return self.config.is_jetson
    
    @property
    def has_nvmpi_h264(self) -> bool:
        """Retorna si hay decodificador NVMPI H264."""
        return self.config.has_nvmpi_h264
    
    @property
    def has_nvmpi_hevc(self) -> bool:
        """Retorna si hay decodificador NVMPI HEVC."""
        return self.config.has_nvmpi_hevc
    
    @property
    def has_nvmpi_vp9(self) -> bool:
        """Retorna si hay decodificador NVMPI VP9."""
        return self.config.has_nvmpi_vp9
    
    # -------------------------------------------------------------------------
    # Métodos de validación
    # -------------------------------------------------------------------------
    
    def _validate_video_path(self, video_path: str) -> bool:
        """Valida que la ruta del video sea segura."""
        return self.validator.validate_video_path(video_path)
    
    # -------------------------------------------------------------------------
    # Métodos de información (delegados a FFmpegProbe)
    # -------------------------------------------------------------------------
    
    def get_video_info(self, video_path: str) -> dict:
        """Obtiene información del video."""
        return self.probe.get_video_info(video_path)
    
    def get_duration(self, video_path: str) -> float:
        """Obtiene la duración del video."""
        return self.probe.get_duration(video_path)
    
    # -------------------------------------------------------------------------
    # Métodos de ejecución (delegados a FFmpegProcess)
    # -------------------------------------------------------------------------
    
    def execute(self, cmd_args: list) -> bool:
        """Ejecuta un comando FFmpeg."""
        return self.process.execute(cmd_args, self.state_manager)
    
    def cancel_current_process(self) -> bool:
        """Cancela el proceso actual."""
        return self.process.cancel_current_process()
    
    # -------------------------------------------------------------------------
    # Métodos de compatibilidad (para mantener API existente)
    # -------------------------------------------------------------------------
    
    @property
    def current_process(self):
        """Propiedad de compatibilidad para el proceso actual."""
        return self.process.current_process
    
    @property
    def set_process_callback(self):
        """Propiedad de compatibilidad para el callback."""
        return self.process.set_process_callback
    
    @set_process_callback.setter
    def set_process_callback(self, value):
        """Setter para el callback."""
        self.process.set_process_callback = value
