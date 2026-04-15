"""
Servicio de autenticación - Lógica de negocio para procesar usuarios y roles
"""
import logging
from typing import Any, Dict, List, Optional

from src.domain.ports.out.services.ITokenDecoder import ITokenDecoder

logger = logging.getLogger(__name__)


class RoleService:
    """
    Servicio para procesar información de usuarios y roles.
    La lógica de negocio es pura; la decodificación JWT se delega a ITokenDecoder.
    """

    def __init__(self, token_decoder: ITokenDecoder):
        self._token_decoder = token_decoder

    def process_user_data(
        self,
        user_info: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Procesa la información del usuario y extrae roles de manera consistente

        Args:
            user_info: Diccionario con información del usuario (de userinfo endpoint)
            access_token: Token JWT para decodificar si user_info no tiene roles

        Returns:
            Diccionario con los datos del usuario listos para la sesión
        """
        roles: List[str] = []
        user_role: Optional[str] = None

        if user_info:
            roles = user_info.get("roles", [])
            user_role = user_info.get("role")

        # Si no hay roles en userinfo, intentar decodificar el JWT
        if not roles and access_token:
            roles, user_role = self._extract_roles_from_token(access_token, user_role)

        # Determinar rol del usuario
        user_role, roles = self._normalize_roles(user_role, roles)

        return {
            "user_id": user_info.get("sub", 1) if user_info else 1,
            "email": user_info.get("email", "") if user_info else "",
            "username": self._extract_username(user_info),
            "user_role": user_role,
            "user_roles": roles,
        }

    def _extract_roles_from_token(
        self, access_token: str, current_role: Optional[str]
    ) -> tuple:
        """Extrae roles del token JWT usando el decoder inyectado."""
        roles: List[str] = []
        try:
            jwt_payload = self._token_decoder.decode(
                access_token, options={"verify_signature": False}
            )
            jwt_roles = jwt_payload.get("roles", [])
            roles = list(set(jwt_roles))

            if not current_role:
                current_role = jwt_payload.get("role")

            logger.info("Roles extraídos del JWT: %s", roles)
        except Exception as e:
            logger.info("Error decodificando JWT: %s", e)

        return roles, current_role

    @staticmethod
    def _extract_username(user_info: Optional[Dict[str, Any]]) -> str:
        """Extrae el username de user_info con fallbacks."""
        if not user_info:
            return "user"

        return (
            user_info.get("preferred_username")
            or user_info.get("name")
            or user_info.get("email", "").split("@")[0]
            or "user"
        )

    @staticmethod
    def _normalize_roles(
        user_role: Optional[str], roles: List[str]
    ) -> tuple:
        """Normaliza los roles al formato esperado por la aplicación."""
        if not user_role and roles:
            if "ROLE_ADMIN" in roles:
                user_role = "admin"
            elif "ROLE_USER" in roles:
                user_role = "user"
            else:
                user_role = "user"

        if user_role and (user_role == "admin" or user_role == "ROLE_ADMIN"):
            user_role = "admin"
            roles = ["ROLE_ADMIN", "ROLE_USER"] if not roles else roles
        else:
            user_role = "user"
            if not roles:
                roles = ["ROLE_USER"]

        return user_role, roles
