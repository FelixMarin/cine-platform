"""
Servicio de información de usuario OAuth2

Maneja la obtención de información del usuario desde el servidor OAuth2.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

from src.adapters.outgoing.services.auth.jwt_token_decoder import JWTTokenDecoder

logger = logging.getLogger(__name__)


class OAuth2UserInfoService:
    """Servicio para obtener información del usuario desde OAuth2"""

    def __init__(self):
        self.oauth2_url = os.environ.get(
            "OAUTH2_URL", "http://oauth2-server:8080"
        ).rstrip("/")
        self._token_decoder = JWTTokenDecoder()

    def get_userinfo(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del usuario desde el servidor OAuth2.

        Args:
            token: Token de acceso

        Returns:
            Diccionario con información del usuario o None si falla
        """
        try:
            userinfo_response = requests.get(
                f"{self.oauth2_url}/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )

            if userinfo_response.status_code != 200:
                logger.warning(
                    f"[OAuth2UserInfoService] userinfo failed: {userinfo_response.status_code}"
                )
                return None

            userinfo_data = userinfo_response.json()

            roles = self._extract_roles_from_token(token)
            if roles:
                userinfo_data["roles"] = roles

            return userinfo_data

        except Exception as e:
            logger.error(f"[OAuth2UserInfoService] Error: {e}")
            return None

    def _extract_roles_from_token(self, token: str) -> list:
        """Extrae los roles del token JWT usando el decoder inyectado."""
        try:
            jwt_payload = self._token_decoder.decode(
                token, options={"verify_signature": False}
            )
            return jwt_payload.get("roles", [])
        except Exception as e:
            logger.info("[OAuth2UserInfoService] Error decoding JWT: %s", e)
            return []

    def revoke_token(self, token: str) -> bool:
        """
        Revoca un token en el servidor OAuth2.

        Args:
            token: Token a revocar

        Returns:
            True si la revocación fue exitosa
        """
        try:
            requests.post(f"{self.oauth2_url}/oauth2/revoke", data={"token": token})
            return True
        except Exception as e:
            logger.error(f"[OAuth2UserInfoService] Error revocando token: {e}")
            return False
