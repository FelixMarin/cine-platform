"""
Caso de uso - Seguimiento de progreso de reproducción
"""
from typing import Optional, List, Dict
from src.core.ports.repositories.progress_repository import IProgressRepository
from src.core.ports.repositories.movie_repository import IMovieRepository
from src.core.ports.repositories.episode_repository import IEpisodeRepository


class TrackProgressUseCase:
    """Caso de uso para rastrear el progreso de reproducción"""
    
    def __init__(
        self,
        progress_repository: IProgressRepository,
        movie_repository: IMovieRepository = None,
        episode_repository: IEpisodeRepository = None
    ):
        self._progress_repository = progress_repository
        self._movie_repository = movie_repository
        self._episode_repository = episode_repository
    
    def update_position(
        self,
        user_id: int,
        media_type: str,
        media_id: int,
        position: int,
        duration: int
    ) -> Dict:
        """
        Actualiza la posición de reproducción
        
        Args:
            user_id: ID del usuario
            media_type: 'movie' o 'episode'
            media_id: ID de la película o episodio
            position: Posición en segundos
            duration: Duración total en segundos
            
        Returns:
            Diccionario con el progreso actualizado
        """
        # Obtener progreso existente o crear nuevo
        progress = self._progress_repository.get_by_user_and_media(
            user_id, media_type, media_id
        )
        
        if progress:
            # Actualizar posición
            return self._progress_repository.update_position(
                user_id, media_type, media_id, position
            )
        else:
            # Crear nuevo registro de progreso
            return self._progress_repository.save({
                'user_id': user_id,
                'media_type': media_type,
                'media_id': media_id,
                'position': position,
                'duration': duration,
                'is_completed': position >= duration * 0.9
            })
    
    def mark_completed(
        self,
        user_id: int,
        media_type: str,
        media_id: int
    ) -> Dict:
        """
        Marca un contenido como completado
        
        Args:
            user_id: ID del usuario
            media_type: 'movie' o 'episode'
            media_id: ID de la película o episodio
            
        Returns:
            Diccionario con el progreso actualizado
        """
        return self._progress_repository.mark_completed(
            user_id, media_type, media_id
        )
    
    def increment_watch_count(
        self,
        user_id: int,
        media_type: str,
        media_id: int
    ) -> Dict:
        """
        Incrementa el contador de reproducciones
        
        Args:
            user_id: ID del usuario
            media_type: 'movie' o 'episode'
            media_id: ID de la película o episodio
            
        Returns:
            Diccionario con el progreso actualizado
        """
        return self._progress_repository.increment_watch_count(
            user_id, media_type, media_id
        )
    
    def get_progress(
        self,
        user_id: int,
        media_type: str,
        media_id: int
    ) -> Optional[Dict]:
        """
        Obtiene el progreso de un contenido específico
        
        Args:
            user_id: ID del usuario
            media_type: 'movie' o 'episode'
            media_id: ID de la película o episodio
            
        Returns:
            Diccionario con el progreso o None
        """
        return self._progress_repository.get_by_user_and_media(
            user_id, media_type, media_id
        )


class GetContinueWatchingUseCase:
    """Caso de uso para obtener 'Seguir viendo'"""
    
    def __init__(
        self,
        progress_repository: IProgressRepository,
        movie_repository: IMovieRepository = None,
        episode_repository: IEpisodeRepository = None
    ):
        self._progress_repository = progress_repository
        self._movie_repository = movie_repository
        self._episode_repository = episode_repository
    
    def execute(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Obtiene los contenidos que el usuario está viendo
        
        Args:
            user_id: ID del usuario
            limit: Límite de resultados
            
        Returns:
            Lista de contenidos con progreso
        """
        # Obtener progresos no completados
        progress_list = self._progress_repository.get_continue_watching(
            user_id, limit
        )
        
        # Enriquecer con información del contenido
        result = []
        for progress in progress_list:
            media_type = progress.get('media_type')
            media_id = progress.get('media_id')
            
            media_info = None
            if media_type == 'movie' and self._movie_repository:
                media_info = self._movie_repository.get_by_id(media_id)
            elif media_type == 'episode' and self._episode_repository:
                media_info = self._episode_repository.get_by_id(media_id)
            
            if media_info:
                result.append({
                    'progress': progress,
                    'media': media_info,
                    'media_type': media_type
                })
        
        return result


class GetWatchedContentUseCase:
    """Caso de uso para obtener contenido visto"""
    
    def __init__(
        self,
        progress_repository: IProgressRepository,
        movie_repository: IMovieRepository = None,
        episode_repository: IEpisodeRepository = None
    ):
        self._progress_repository = progress_repository
        self._movie_repository = movie_repository
        self._episode_repository = episode_repository
    
    def execute(self, user_id: int, limit: int = 20) -> List[Dict]:
        """
        Obtiene los contenidos completados por el usuario
        
        Args:
            user_id: ID del usuario
            limit: Límite de resultados
            
        Returns:
            Lista de contenidos completados
        """
        # Obtener progresos completados
        progress_list = self._progress_repository.get_completed(
            user_id, limit
        )
        
        # Enriquecer con información del contenido
        result = []
        for progress in progress_list:
            media_type = progress.get('media_type')
            media_id = progress.get('media_id')
            
            media_info = None
            if media_type == 'movie' and self._movie_repository:
                media_info = self._movie_repository.get_by_id(media_id)
            elif media_type == 'episode' and self._episode_repository:
                media_info = self._episode_repository.get_by_id(media_id)
            
            if media_info:
                result.append({
                    'progress': progress,
                    'media': media_info,
                    'media_type': media_type
                })
        
        return result
