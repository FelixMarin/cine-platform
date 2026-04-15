"""
Caso de uso - Logout
"""

from src.domain.ports.out.services.auth_service import IAuthService


class LogoutUseCase:
    """Caso de uso para cerrar sesión"""

    def __init__(self, auth_service: IAuthService):
        self._auth_service = auth_service

    def execute(self, user_id: int) -> bool:
        """
        Cierra sesión

        Args:
            user_id: ID del usuario

        Returns:
            True si tuvo éxito
        """
        return self._auth_service.logout(user_id)
