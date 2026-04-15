"""
Adaptador de salida - Servicio de autenticación
Implementación básica que usa credenciales de entorno
"""
import os
import secrets
from typing import Dict, List, Optional, Tuple

from src.domain.ports.out.services.auth_service import IAuthService


class AuthService(IAuthService):
    """Servicio de autenticación básico con credenciales de entorno"""

    def __init__(self):
        self._valid_user = os.environ.get('APP_USER', 'default-user')
        self._valid_password = os.environ.get('APP_PASSWORD', 'default-user-password')
        self._tokens = {}  # Almacén temporal de tokens

    def _determine_user_role(self, roles: List[str]) -> str:
        """
        Determina el rol del usuario basándose en los roles del token JWT.
        
        Args:
            roles: Lista de roles del token JWT (ej: ['ROLE_USER', 'ROLE_ADMIN'])
            
        Returns:
            'admin' si tiene ROLE_ADMIN, 'user' en caso contrario
        """
        if 'ROLE_ADMIN' in roles:
            return 'admin'
        return 'user'

    def _decode_jwt_payload(self, token: str) -> Optional[Dict]:
        """
        Decodifica el payload de un JWT token.
        
        Args:
            token: JWT token a decodificar
            
        Returns:
            Payload decodificado o None si falla
        """
        try:
            # Intentar importar PyJWT
            import jwt
            # Decodificar sin verificar firma (el servidor OAuth ya lo hizo)
            # El token viene del propio servidor OAuth, confiamos en él
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except ImportError:
            # Fallback: decodificar manualmente el payload (base64)
            try:
                parts = token.split('.')
                if len(parts) != 3:
                    return None
                # Decodificar el payload (parte central)
                import base64
                import json
                payload_b64 = parts[1]
                # Añadir padding si es necesario
                padding = 4 - (len(payload_b64) % 4)
                if padding != 4:
                    payload_b64 += '=' * padding
                payload_json = base64.urlsafe_b64decode(payload_b64)
                return json.loads(payload_json)
            except Exception:
                return None
        except Exception:
            return None

    def extract_roles_from_token(self, token: str) -> Tuple[str, List[str]]:
        """
        Extrae los roles del token JWT y determina el rol del usuario.
        
        Args:
            token: JWT token del OAuth2 server
            
        Returns:
            Tupla (user_role, roles_list)
            - user_role: 'admin' o 'user'
            - roles_list: Lista completa de roles del token
        """
        payload = self._decode_jwt_payload(token)

        if not payload:
            # Si no se puede decodificar, por defecto es usuario
            return 'user', []

        # Obtener roles del payload (puede venir como 'roles' o 'realm_access.roles')
        roles = payload.get('roles', [])

        # Si viene como string, convertir a lista
        if isinstance(roles, str):
            roles = [roles]

        # Determinar el rol del usuario
        user_role = self._determine_user_role(roles)

        return user_role, roles

    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Inicia sesión con email y password
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            
        Returns:
            (success, user_data)
        """
        if email == self._valid_user and password == self._valid_password:
            user_data = {
                'id': 1,
                'email': email,
                'username': email,
                'role': 'admin'
            }
            return True, user_data
        return False, None

    def logout(self, user_id: int) -> bool:
        """Cierra sesión"""
        # Limpiar tokens del usuario
        self._tokens = {k: v for k, v in self._tokens.items() if v.get('user_id') != user_id}
        return True

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica un token de autenticación"""
        if token in self._tokens:
            token_data = self._tokens[token]
            return token_data.get('user_data')
        return None

    def refresh_token(self, token: str) -> Optional[str]:
        """Refresca un token de autenticación"""
        if token in self._tokens:
            # Generar nuevo token
            new_token = secrets.token_urlsafe(32)
            user_data = self._tokens[token].get('user_data')
            self._tokens[new_token] = {
                'user_id': user_data.get('id'),
                'user_data': user_data
            }
            # Eliminar token antiguo
            del self._tokens[token]
            return new_token
        return None

    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Obtiene los datos del usuario desde un token"""
        return self.verify_token(token)

    def create_token(self, user_id: int) -> Optional[str]:
        """Crea un token para un usuario"""
        token = secrets.token_urlsafe(32)
        user_data = {
            'id': user_id,
            'role': 'admin'
        }
        self._tokens[token] = {
            'user_id': user_id,
            'user_data': user_data
        }
        return token
