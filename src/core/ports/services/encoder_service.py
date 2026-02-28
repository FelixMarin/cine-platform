"""
Puerto - Interfaz para servicio de codificación de video
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class IEncoderService(ABC):
    """Puerto para servicios de codificación de video (FFmpeg)"""
    
    @abstractmethod
    def get_video_info(self, file_path: str) -> Dict:
        """Obtiene información de un archivo de video"""
        pass
    
    @abstractmethod
    def get_duration(self, file_path: str) -> Optional[float]:
        """Obtiene la duración de un video en segundos"""
        pass
    
    @abstractmethod
    def optimize_video(
        self,
        input_path: str,
        output_path: str,
        profile: str = "balanced"
    ) -> bool:
        """Optimiza un video usando un perfil específico"""
        pass
    
    @abstractmethod
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: str = "00:00:01"
    ) -> bool:
        """Genera un thumbnail de un video"""
        pass
    
    @abstractmethod
    def estimate_size(self, input_path: str, profile: str) -> Optional[Dict]:
        """Estima el tamaño final de un video optimizado"""
        pass
    
    @abstractmethod
    def get_available_profiles(self) -> Dict:
        """Obtiene los perfiles de optimización disponibles"""
        pass
