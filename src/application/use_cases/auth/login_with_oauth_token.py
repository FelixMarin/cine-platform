"""
Caso de uso - Login con token OAuth
"""

from typing import Dict, Optional, Tuple

from src.domain.ports.out.services.auth_service import IAuthService


class LoginWithOAuthTokenUseCase:
    """Caso de uso para login usando token JWT del OAuth2 server"""

    def __init__(self, auth_service: IAuthService):
        self._auth_service = auth_service

    def execute(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Login usando el token JWT del OAuth2 server.
        Extrae los roles del token y determina el rol del usuario.

        Args:
            token: JWT token del OAuth2 server

        Returns:
            Tupla (success, user_data)
        """
        # Extraer roles del token usando el auth service
        user_role, roles = self._auth_service.extract_roles_from_token(token)

        user_data = {
            "id": 1,  # ID generado - debería venir del token o generarse apropiadamente
            "username": "oauth_user",  # Debería extraerse del token
            "email": "",  # Debería extraerse del token
            "role": user_role,
            "roles": roles,  # Lista completa de roles del token
        }

        return True, user_data
