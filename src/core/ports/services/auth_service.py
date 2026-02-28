"""
Puerto - Interfaz para servicio de autenticación
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict


class IAuthService(ABC):
    """Puerto para servicios de autenticación"""
    
    @abstractmethod
    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Inicia sesión con email y password
        Returns: (success, user_data)
        """
        pass
    
    @abstractmethod
    def logout(self, user_id: int) -> bool:
        """Cierra sesión"""
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica un token de autenticación"""
        pass
    
    @abstractmethod
    def refresh_token(self, token: str) -> Optional[str]:
        """Refresca un token de autenticación"""
        pass
    
    @abstractmethod
    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Obtiene los datos del usuario desde un token"""
        pass
    
    @abstractmethod
    def create_token(self, user_id: int) -> Optional[str]:
        """Crea un token para un usuario"""
        pass
