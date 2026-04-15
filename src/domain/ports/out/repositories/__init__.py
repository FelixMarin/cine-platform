"""
Puertos - Repositorios del dominio
"""
from src.domain.ports.out.repositories.episode_repository import IEpisodeRepository
from src.domain.ports.out.repositories.movie_repository import IMovieRepository
from src.domain.ports.out.repositories.progress_repository import IProgressRepository
from src.domain.ports.out.repositories.serie_repository import ISerieRepository
from src.domain.ports.out.repositories.user_repository import IUserRepository

__all__ = [
    'IMovieRepository',
    'ISerieRepository',
    'IEpisodeRepository',
    'IUserRepository',
    'IProgressRepository',
]
