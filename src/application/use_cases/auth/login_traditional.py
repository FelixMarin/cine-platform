"""
Caso de uso - Login tradicional con email y password
"""

from typing import Dict, Optional, Tuple

from src.domain.ports.out.repositories.user_repository import IUserRepository
from src.domain.ports.out.services.auth_service import IAuthService


class LoginUseCase:
    """Caso de uso para iniciar sesión con email y password"""

    def __init__(self, auth_service: IAuthService, user_repository: IUserRepository):
        self._auth_service = auth_service
        self._user_repository = user_repository

    def execute(self, email: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Inicia sesión con email y password

        Args:
            email: Email del usuario
            password: Contraseña del usuario

        Returns:
            Tupla (success, user_data)
        """
        # Intentar login con el servicio de auth
        success, user_data = self._auth_service.login(email, password)

        if success and user_data:
            # Actualizar último login
            user_id = user_data.get("id")
            if user_id:
                self._user_repository.update_last_login(user_id)

        return success, user_data
