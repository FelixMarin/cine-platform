from abc import ABC, abstractmethod
from typing import Optional, Dict, List


class IAppUserRepository(ABC):
    """Puerto para el repositorio de usuarios de la aplicación"""

    @abstractmethod
    def get_by_id(self, app_user_id: int) -> Optional[Dict]:
        """Obtiene perfil por ID interno de la app"""
        pass

    @abstractmethod
    def get_by_oauth_id(self, oauth_user_id: int) -> Optional[Dict]:
        """Obtiene perfil por ID de OAuth2"""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[Dict]:
        """Obtiene perfil por nombre de usuario"""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict]:
        """Obtiene perfil por email"""
        pass

    @abstractmethod
    def create_from_oauth(self, oauth_data: Dict) -> int:
        """
        Crea un perfil a partir de datos OAuth2
        Args:
            oauth_data: {
                'id': int,           # ID en oauth2_db
                'username': str,
                'email': str,
                'roles': List[str],
                'display_name': str (opcional)
            }
        Returns:
            ID del nuevo perfil en cine_app_db
        """
        pass

    @abstractmethod
    def update_profile(self, app_user_id: int, data: Dict) -> bool:
        """
        Actualiza datos del perfil (solo campos permitidos)
        Args:
            data: {
                'display_name': str (opcional),
                'bio': str (opcional),
                'privacy_level': str (opcional),
                'avatar_url': str (opcional),
                'settings': dict (opcional)
            }
        """
        pass

    @abstractmethod
    def update_last_active(self, app_user_id: int) -> None:
        """Actualiza timestamp de última actividad"""
        pass

    @abstractmethod
    def user_exists(self, oauth_user_id: int) -> bool:
        """Verifica si un usuario ya tiene perfil"""
        pass
