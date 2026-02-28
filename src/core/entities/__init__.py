"""
Entidades del dominio - Core de Cine Platform
"""
from src.core.entities.movie import Movie
from src.core.entities.serie import Serie, Episode
from src.core.entities.user import User, UserRole, UserPreferences
from src.core.entities.progress import Progress, MediaType

__all__ = [
    'Movie',
    'Serie',
    'Episode',
    'User',
    'UserRole',
    'UserPreferences',
    'Progress',
    'MediaType',
]
