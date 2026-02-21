"""
Puertos - Repositorios del dominio
"""
from src.core.ports.repositories.movie_repository import IMovieRepository
from src.core.ports.repositories.serie_repository import ISerieRepository
from src.core.ports.repositories.episode_repository import IEpisodeRepository
from src.core.ports.repositories.user_repository import IUserRepository
from src.core.ports.repositories.progress_repository import IProgressRepository

__all__ = [
    'IMovieRepository',
    'ISerieRepository',
    'IEpisodeRepository',
    'IUserRepository',
    'IProgressRepository',
]
