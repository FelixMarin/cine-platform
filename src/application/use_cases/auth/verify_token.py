"""
Caso de uso - Verificación de token
"""

from typing import Dict, Optional

from src.domain.ports.out.services.auth_service import IAuthService


class VerifyTokenUseCase:
    """Caso de uso para verificar un token de autenticación"""

    def __init__(self, auth_service: IAuthService):
        self._auth_service = auth_service

    def execute(self, token: str) -> Optional[Dict]:
        """
        Verifica un token de autenticación

        Args:
            token: Token JWT a verificar

        Returns:
            Datos del token si es válido, None si no
        """
        return self._auth_service.verify_token(token)
