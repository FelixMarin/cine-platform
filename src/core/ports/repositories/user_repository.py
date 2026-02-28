"""
Puerto - Interfaz para repositorio de usuarios
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict


class IUserRepository(ABC):
    """Puerto para el repositorio de usuarios"""
    
    @abstractmethod
    def list_all(self) -> List[Dict]:
        """Lista todos los usuarios"""
        pass
    
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[Dict]:
        """Obtiene un usuario por su ID"""
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict]:
        """Obtiene un usuario por su email"""
        pass
    
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[Dict]:
        """Obtiene un usuario por su nombre de usuario"""
        pass
    
    @abstractmethod
    def get_by_oauth(self, provider: str, oauth_id: str) -> Optional[Dict]:
        """Obtiene un usuario por su ID de OAuth"""
        pass
    
    @abstractmethod
    def save(self, user_data: Dict) -> Dict:
        """Guarda o actualiza un usuario"""
        pass
    
    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Elimina un usuario"""
        pass
    
    @abstractmethod
    def update_preferences(self, user_id: int, preferences: Dict) -> Dict:
        """Actualiza las preferencias de un usuario"""
        pass
    
    @abstractmethod
    def update_last_login(self, user_id: int) -> bool:
        """Actualiza la fecha del último login"""
        pass
