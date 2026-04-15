"""
Puerto - Decodificador de tokens JWT
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ITokenDecoder(ABC):
    """Puerto para decodificar tokens JWT sin depender de la librería jwt"""

    @abstractmethod
    def decode(self, token: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Decodifica un token JWT y devuelve el payload.

        Args:
            token: Token JWT a decodificar
            options: Opciones de decodificación (ej: {"verify_signature": False})

        Returns:
            Payload decodificado como diccionario
        """
        pass
