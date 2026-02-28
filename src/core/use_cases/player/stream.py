"""
Caso de uso - Streaming de video
"""
import os
from typing import Optional, Tuple
from src.core.ports.repositories.movie_repository import IMovieRepository
from src.core.ports.repositories.episode_repository import IEpisodeRepository


class StreamMovieUseCase:
    """Caso de uso para streaming de películas"""
    
    def __init__(
        self,
        movie_repository: IMovieRepository,
        progress_repository: 'IProgressRepository' = None
    ):
        self._movie_repository = movie_repository
        self._progress_repository = progress_repository
    
    def execute(self, movie_id: int) -> Optional[dict]:
        """
        Obtiene la información necesaria para reproducir una película
        
        Args:
            movie_id: ID de la película
            
        Returns:
            Diccionario con información de reproducción
        """
        movie = self._movie_repository.get_by_id(movie_id)
        
        if not movie:
            return None
        
        # Verificar que el archivo existe
        if not os.path.exists(movie['path']):
            return None
        
        # Obtener progreso si está disponible
        progress = None
        if self._progress_repository:
            # Asumimos usuario por defecto (0) si no hay auth
            progress = self._progress_repository.get_by_user_and_media(
                0, 'movie', movie_id
            )
        
        return {
            'movie': movie,
            'progress': progress,
            'stream_url': f"/api/stream/movie/{movie_id}"
        }
    
    def get_stream_info(self, movie_id: int) -> Optional[Tuple[str, int]]:
        """
        Obtiene la ruta y tamaño del archivo para streaming
        
        Returns:
            Tupla (ruta, tamaño) o None
        """
        movie = self._movie_repository.get_by_id(movie_id)
        
        if not movie or not os.path.exists(movie['path']):
            return None
        
        file_size = os.path.getsize(movie['path'])
        return movie['path'], file_size


class StreamEpisodeUseCase:
    """Caso de uso para streaming de episodios"""
    
    def __init__(
        self,
        episode_repository: IEpisodeRepository,
        progress_repository: 'IProgressRepository' = None
    ):
        self._episode_repository = episode_repository
        self._progress_repository = progress_repository
    
    def execute(self, episode_id: int) -> Optional[dict]:
        """
        Obtiene la información necesaria para reproducir un episodio
        
        Args:
            episode_id: ID del episodio
            
        Returns:
            Diccionario con información de reproducción
        """
        episode = self._episode_repository.get_by_id(episode_id)
        
        if not episode:
            return None
        
        # Verificar que el archivo existe
        if not os.path.exists(episode['path']):
            return None
        
        # Obtener progreso si está disponible
        progress = None
        if self._progress_repository:
            progress = self._progress_repository.get_by_user_and_media(
                0, 'episode', episode_id
            )
        
        return {
            'episode': episode,
            'progress': progress,
            'stream_url': f"/api/stream/episode/{episode_id}"
        }
    
    def get_stream_info(self, episode_id: int) -> Optional[Tuple[str, int]]:
        """
        Obtiene la ruta y tamaño del archivo para streaming
        
        Returns:
            Tupla (ruta, tamaño) o None
        """
        episode = self._episode_repository.get_by_id(episode_id)
        
        if not episode or not os.path.exists(episode['path']):
            return None
        
        file_size = os.path.getsize(episode['path'])
        return episode['path'], file_size
