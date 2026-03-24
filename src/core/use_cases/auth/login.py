"""
Caso de uso - Autenticación
"""
from typing import Optional, Dict, Tuple, List
from src.core.ports.services.auth_service import IAuthService
from src.core.ports.repositories.user_repository import IUserRepository


def determine_user_role(roles: List[str]) -> str:
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


class LoginUseCase:
    """Caso de uso para iniciar sesión"""
    
    def __init__(
        self,
        auth_service: IAuthService,
        user_repository: IUserRepository = None
    ):
        self._auth_service = auth_service
        self._user_repository = user_repository
    
    def execute(self, email: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Inicia sesión con email y password
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            
        Returns:
            Tupla (success, user_data)
        """
        # Intentar login con el servicio de auth
        success, user_data = self._auth_service.login(email, password)
        
        if success and user_data and self._user_repository:
            # Actualizar último login
            user_id = user_data.get('id')
            if user_id:
                self._user_repository.update_last_login(user_id)
        
        return success, user_data
    
    def oauth_login(
        self,
        provider: str,
        oauth_id: str,
        email: str,
        username: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Login o registro con OAuth
        
        Args:
            provider: Proveedor OAuth (google, github, etc.)
            oauth_id: ID del usuario en el proveedor
            email: Email del usuario
            username: Nombre de usuario
            
        Returns:
            Tupla (success, user_data)
        """
        # Buscar usuario existente por OAuth
        if self._user_repository:
            user = self._user_repository.get_by_oauth(provider, oauth_id)
            
            if user:
                # Actualizar último login
                self._user_repository.update_last_login(user['id'])
                return True, user
            
            # Crear nuevo usuario
            new_user = {
                'email': email,
                'username': username,
                'oauth_provider': provider,
                'oauth_id': oauth_id,
                'role': 'user',
                'is_active': True
            }
            
            return True, self._user_repository.save(new_user)
        
        return False, None
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica un token de autenticación"""
        return self._auth_service.verify_token(token)
    
    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Obtiene el usuario desde un token"""
        return self._auth_service.get_user_from_token(token)
    
    def login_with_oauth_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Login usando el token JWT del OAuth2 server.
        Extrae los roles del token y determina el rol del usuario.
        
        Args:
            token: JWT token del OAuth2 server
            
        Returns:
            Tupla (success, user_data)
        """
        # Intentar usar el método del auth_service si está disponible
        if hasattr(self._auth_service, 'extract_roles_from_token'):
            user_role, roles = self._auth_service.extract_roles_from_token(token)
            
            user_data = {
                'id': 1,  # ID generado
                'username': 'oauth_user',
                'email': '',
                'role': user_role,
                'roles': roles  # Lista completa de roles del token
            }
            return True, user_data
        
        # Fallback: si no hay método disponible
        return False, None


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
