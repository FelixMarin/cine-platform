"""
Adaptador de salida - Decodificador JWT usando PyJWT
Implementación concreta de ITokenDecoder
"""

import jwt
import logging
from typing import Any, Dict, Optional

from src.domain.ports.out.services.ITokenDecoder import ITokenDecoder

logger = logging.getLogger(__name__)


class JWTTokenDecoder(ITokenDecoder):
    """Decodifica tokens JWT usando la librería PyJWT"""

    def decode(
        self,
        token: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Decodifica un token JWT y devuelve el payload.

        Args:
            token: Token JWT a decodificar
            options: Opciones de decodificación (ej: {"verify_signature": False})

        Returns:
            Payload decodificado como diccionario

        Raises:
            jwt.InvalidTokenError: Si el token no es válido
        """
        decode_options = options or {"verify_signature": False}

        return jwt.decode(token, options=decode_options)
