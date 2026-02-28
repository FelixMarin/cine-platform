"""
Adaptador de salida - Servicio de autenticación
Implementación básica que usa credenciales de entorno
"""
import os
import secrets
from typing import Tuple, Optional, Dict
from src.core.ports.services.auth_service import IAuthService


class AuthService(IAuthService):
    """Servicio de autenticación básico con credenciales de entorno"""
    
    def __init__(self):
        self._valid_user = os.environ.get('APP_USER', 'admin')
        self._valid_password = os.environ.get('APP_PASSWORD', 'Admin1')
        self._tokens = {}  # Almacén temporal de tokens
    
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
