"""
Caso de uso - Obtener usuario desde token
"""

from typing import Dict, Optional

from src.domain.ports.out.services.auth_service import IAuthService


class GetUserFromTokenUseCase:
    """Caso de uso para obtener el usuario desde un token"""

    def __init__(self, auth_service: IAuthService):
        self._auth_service = auth_service

    def execute(self, token: str) -> Optional[Dict]:
        """
        Obtiene el usuario desde un token

        Args:
            token: Token JWT

        Returns:
            Datos del usuario si el token es válido, None si no
        """
        return self._auth_service.get_user_from_token(token)
