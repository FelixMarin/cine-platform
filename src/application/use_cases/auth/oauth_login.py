"""
Caso de uso - Login con OAuth
"""

from typing import Dict, Optional, Tuple

from src.domain.ports.out.repositories.user_repository import IUserRepository


class OAuthLoginUseCase:
    """Caso de uso para login o registro con OAuth"""

    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository

    def execute(
        self, provider: str, oauth_id: str, email: str, username: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Login o registro con OAuth

        Args:
            provider: Proveedor OAuth (google, github, etc.)
            oauth_id: ID del usuario en el proveedor
            email: Email del usuario
            username: Nombre de usuario

        Returns:
            Tupla (success, user_data)
        """
        # Buscar usuario existente por OAuth
        user = self._user_repository.get_by_oauth(provider, oauth_id)

        if user:
            # Actualizar último login
            self._user_repository.update_last_login(user["id"])
            return True, user

        # Crear nuevo usuario
        new_user = {
            "email": email,
            "username": username,
            "oauth_provider": provider,
            "oauth_id": oauth_id,
            "role": "user",
            "is_active": True,
        }

        return True, self._user_repository.save(new_user)
