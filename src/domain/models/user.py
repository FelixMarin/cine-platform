"""
Entidad User - Representa un usuario del sistema
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class UserRole(Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


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


class UserPreferences:
    """Preferencias del usuario"""

    def __init__(
        self,
        default_quality: str = "balanced",
        autoplay: bool = True,
        subtitles: bool = True,
        language: str = "es"
    ):
        self.default_quality = default_quality
        self.autoplay = autoplay
        self.subtitles = subtitles
        self.language = language

    def to_dict(self) -> Dict:
        return {
            'default_quality': self.default_quality,
            'autoplay': self.autoplay,
            'subtitles': self.subtitles,
            'language': self.language,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreferences':
        if not data:
            return cls()
        return cls(**data)


@dataclass
class User:
    """Entidad que representa un usuario del sistema"""

    id: Optional[int] = None
    email: str = ""
    username: str = ""
    role: UserRole = UserRole.USER
    roles: List[str] = field(default_factory=list)  # Lista completa de roles del token JWT
    is_active: bool = True

    # Preferencias
    preferences: UserPreferences = field(default_factory=UserPreferences)

    # OAuth info
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None

    # Avatar
    avatar_url: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if isinstance(self.role, str):
            self.role = UserRole(self.role)
        if isinstance(self.preferences, dict):
            self.preferences = UserPreferences.from_dict(self.preferences)

    @property
    def is_admin(self) -> bool:
        """Verifica si el usuario es administrador"""
        return self.role == UserRole.ADMIN

    @property
    def display_name(self) -> str:
        """Nombre para mostrar"""
        return self.username or self.email.split('@')[0]

    def to_dict(self) -> Dict:
        """Convierte la entidad a diccionario"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'role': self.role.value if isinstance(self.role, UserRole) else self.role,
            'roles': self.roles,  # Lista completa de roles del token JWT
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'preferences': self.preferences.to_dict() if self.preferences else {},
            'oauth_provider': self.oauth_provider,
            'oauth_id': self.oauth_id,
            'avatar_url': self.avatar_url,
            'display_name': self.display_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Crea una entidad desde un diccionario"""
        if 'preferences' in data and isinstance(data['preferences'], dict):
            data['preferences'] = UserPreferences.from_dict(data['preferences'])
        if 'role' in data and isinstance(data['role'], str):
            data['role'] = UserRole(data['role'])
        # Soporte para lista de roles del token JWT
        if 'roles' not in data:
            data['roles'] = []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
