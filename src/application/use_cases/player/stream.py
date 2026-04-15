"""
Caso de uso - Streaming de video
"""

from typing import Optional, Tuple

from src.domain.ports.out.repositories.episode_repository import IEpisodeRepository
from src.domain.ports.out.repositories.movie_repository import IMovieRepository
from src.domain.ports.out.repositories.progress_repository import IProgressRepository
from src.domain.ports.out.services.IFileFinder import IFileFinder


class StreamMovieUseCase:
    """Caso de uso para streaming de películas"""

    def __init__(
        self,
        movie_repository: IMovieRepository,
        progress_repository: IProgressRepository,
        file_finder: IFileFinder,
    ):
        self._movie_repository = movie_repository
        self._progress_repository = progress_repository
        self._file_finder = file_finder

    def execute(self, movie_id: int, user_id: int) -> Optional[dict]:
        """
        Obtiene la información necesaria para reproducir una película

        Args:
            movie_id: ID de la película
            user_id: ID del usuario

        Returns:
            Diccionario con información de reproducción
        """
        movie = self._movie_repository.get_by_id(movie_id)

        if not movie:
            return None

        # Verificar que el archivo existe
        if not self._file_finder.file_exists(movie["path"]):
            return None

        # Obtener progreso del usuario
        progress = self._progress_repository.get_by_user_and_media(
            user_id, "movie", movie_id
        )

        return {
            "movie": movie,
            "progress": progress,
            "stream_url": f"/api/stream/movie/{movie_id}",
        }

    def get_stream_info(self, movie_id: int) -> Optional[Tuple[str, int]]:
        """
        Obtiene la ruta y tamaño del archivo para streaming

        Returns:
            Tupla (ruta, tamaño) o None
        """
        movie = self._movie_repository.get_by_id(movie_id)

        if not movie:
            return None

        if not self._file_finder.file_exists(movie["path"]):
            return None

        file_size = self._file_finder.get_file_size(movie["path"])

        return movie["path"], file_size


class StreamEpisodeUseCase:
    """Caso de uso para streaming de episodios"""

    def __init__(
        self,
        episode_repository: IEpisodeRepository,
        progress_repository: IProgressRepository,
        file_finder: IFileFinder,
    ):
        self._episode_repository = episode_repository
        self._progress_repository = progress_repository
        self._file_finder = file_finder

    def execute(self, episode_id: int, user_id: int) -> Optional[dict]:
        """
        Obtiene la información necesaria para reproducir un episodio

        Args:
            episode_id: ID del episodio
            user_id: ID del usuario

        Returns:
            Diccionario con información de reproducción
        """
        episode = self._episode_repository.get_by_id(episode_id)

        if not episode:
            return None

        # Verificar que el archivo existe
        if not self._file_finder.file_exists(episode["path"]):
            return None

        # Obtener progreso del usuario
        progress = self._progress_repository.get_by_user_and_media(
            user_id, "episode", episode_id
        )

        return {
            "episode": episode,
            "progress": progress,
            "stream_url": f"/api/stream/episode/{episode_id}",
        }

    def get_stream_info(self, episode_id: int) -> Optional[Tuple[str, int]]:
        """
        Obtiene la ruta y tamaño del archivo para streaming

        Returns:
            Tupla (ruta, tamaño) o None
        """
        episode = self._episode_repository.get_by_id(episode_id)

        if not episode:
            return None

        if not self._file_finder.file_exists(episode["path"]):
            return None

        file_size = self._file_finder.get_file_size(episode["path"])

        return episode["path"], file_size
