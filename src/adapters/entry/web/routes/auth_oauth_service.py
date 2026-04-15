"""
Servicio OAuth2

Maneja las operaciones de OAuth2: exchange token, refresh, userinfo.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class OAuth2Service:
    """Servicio para operaciones OAuth2"""

    def __init__(self):
        self.oauth2_url = os.environ.get(
            "OAUTH2_URL", "http://oauth2-server:8080"
        ).rstrip("/")
        self.client_id = os.environ.get("OAUTH2_CLIENT_ID", "cine-platform")
        self.client_secret = os.environ.get("OAUTH2_CLIENT_SECRET", "cine-platform")

    def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Intercambia código de autorización por token.

        Args:
            code: Código de autorización
            code_verifier: Verificador de código PKCE
            redirect_uri: URI de redirección

        Returns:
            Diccionario con datos del token

        Raises:
            Exception: Si el intercambio falla
        """
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)

        response = requests.post(
            f"{self.oauth2_url}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=auth,
        )

        if response.status_code != 200:
            logger.error(f"[OAuth2Service] Error exchanging code: {response.text}")
            raise Exception(f"Error intercambiando código: {response.status_code}")

        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresca el token de acceso.

        Args:
            refresh_token: Token de refresco

        Returns:
            Diccionario con nuevos datos del token

        Raises:
            Exception: Si el refresh falla
        """
        response = requests.post(
            f"{self.oauth2_url}/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"[OAuth2Service] Error refreshing token: {response.text}")
            raise Exception(f"Error refrescando token: {response.status_code}")

        return response.json()

    def get_userinfo(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del usuario desde el servidor OAuth2.

        Args:
            access_token: Token de acceso

        Returns:
            Diccionario con información del usuario o None si falla
        """
        try:
            response = requests.get(
                f"{self.oauth2_url}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 200:
                return response.json()
            logger.warning(
                f"[OAuth2Service] Error getting userinfo: {response.status_code}"
            )
        except Exception as e:
            logger.warning(f"[OAuth2Service] Exception getting userinfo: {e}")
        return None

    def get_basic_auth(self) -> tuple:
        """
        Obtiene credenciales para Basic Auth.

        Returns:
            Tupla (client_id, client_secret)
        """
        return (self.client_id, self.client_secret)
