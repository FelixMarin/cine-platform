"""
Servicio de flujo OAuth2

Maneja la generación de code_verifier, code_challenge y state para OAuth2.
"""

import base64
import hashlib
import logging
import secrets
from typing import Tuple

logger = logging.getLogger(__name__)


class OAuth2FlowService:
    """Servicio para gestionar el flujo OAuth2"""

    @staticmethod
    def generate_code_verifier() -> str:
        """
        Genera un code_verifier aleatorio para PKCE.

        Returns:
            Code verifier aleatorio
        """
        return secrets.token_urlsafe(64)[:128]

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """
        Genera un code_challenge a partir del verifier usando SHA256.

        Args:
            verifier: Code verifier

        Returns:
            Code challenge codificada en base64url
        """
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def generate_state() -> str:
        """
        Genera un state aleatorio para protección CSRF.

        Returns:
            State aleatorio
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_pkce_pair() -> Tuple[str, str]:
        """
        Genera un par de code_verifier y code_challenge.

        Returns:
            Tupla (code_verifier, code_challenge)
        """
        verifier = OAuth2FlowService.generate_code_verifier()
        challenge = OAuth2FlowService.generate_code_challenge(verifier)
        return verifier, challenge

    @staticmethod
    def verify_state(state: str, stored_state: str) -> bool:
        """
        Verifica que el state coincida.

        Args:
            state: State recibido
            stored_state: State almacenado

        Returns:
            True si coinciden
        """
        if not state or not stored_state:
            logger.warning("[OAuth2FlowService] State vacío")
            return False
        return state == stored_state
