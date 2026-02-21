"""
Puerto - Interfaz para repositorio de progreso de reproducción
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict


class IProgressRepository(ABC):
    """Puerto para el repositorio de progreso de reproducción"""
    
    @abstractmethod
    def get_by_user_and_media(self, user_id: int, media_type: str, media_id: int) -> Optional[Dict]:
        """Obtiene el progreso de un usuario para un contenido específico"""
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: int) -> List[Dict]:
        """Obtiene todo el progreso de un usuario"""
        pass
    
    @abstractmethod
    def get_continue_watching(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Obtiene los contenidos que el usuario está viendo (no completados)"""
        pass
    
    @abstractmethod
    def get_completed(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Obtiene los contenidos completados por el usuario"""
        pass
    
    @abstractmethod
    def save(self, progress_data: Dict) -> Dict:
        """Guarda o actualiza el progreso"""
        pass
    
    @abstractmethod
    def update_position(self, user_id: int, media_type: str, media_id: int, position: int) -> Dict:
        """Actualiza la posición de reproducción"""
        pass
    
    @abstractmethod
    def mark_completed(self, user_id: int, media_type: str, media_id: int) -> Dict:
        """Marca un contenido como completado"""
        pass
    
    @abstractmethod
    def delete(self, progress_id: int) -> bool:
        """Elimina un registro de progreso"""
        pass
    
    @abstractmethod
    def delete_by_media(self, media_type: str, media_id: int) -> bool:
        """Elimina el progreso de un contenido para todos los usuarios"""
        pass
    
    @abstractmethod
    def increment_watch_count(self, user_id: int, media_type: str, media_id: int) -> Dict:
        """Incrementa el contador de reproducciones"""
        pass
