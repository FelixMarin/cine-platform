"""
Tests para casos de uso de Player
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.use_cases.player import (
    StreamMovieUseCase,
    TrackProgressUseCase,
    GetContinueWatchingUseCase,
    GetWatchedContentUseCase
)


class MockMovieRepository:
    MOVIES = {
        1: {'id': 1, 'title': 'Test Movie', 'path': '/path/to/movie.mkv'}
    }
    
    def get_by_id(self, movie_id):
        return self.MOVIES.get(movie_id)


class MockEpisodeRepository:
    def get_by_id(self, episode_id):
        if episode_id == 1:
            return {'id': 1, 'title': 'Test Episode', 'path': '/path/to/episode.mkv'}
        return None


class MockProgressRepository:
    def __init__(self):
        self.progress = {}
    
    def get_by_user_and_media(self, user_id, media_type, media_id):
        key = f"{user_id}-{media_type}-{media_id}"
        return self.progress.get(key)
    
    def save(self, data):
        key = f"{data['user_id']}-{data['media_type']}-{data['media_id']}"
        self.progress[key] = data
        return data
    
    def update_position(self, user_id, media_type, media_id, position):
        key = f"{user_id}-{media_type}-{media_id}"
        if key in self.progress:
            self.progress[key]['position'] = position
        return self.progress.get(key, {})
    
    def mark_completed(self, user_id, media_type, media_id):
        key = f"{user_id}-{media_type}-{media_id}"
        if key in self.progress:
            self.progress[key]['is_completed'] = True
        return self.progress.get(key, {})
    
    def get_continue_watching(self, user_id, limit=10):
        return [p for p in self.progress.values() if not p.get('is_completed')]
    
    def get_completed(self, user_id, limit=20):
        return [p for p in self.progress.values() if p.get('is_completed')]


class TestStreamMovieUseCase:
    """Tests para StreamMovieUseCase"""
    
    @patch('os.path.exists')
    def test_execute_success(self, mock_exists):
        """Test de ejecución exitosa"""
        mock_exists.return_value = True
        
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        use_case = StreamMovieUseCase(movie_repo, progress_repo)
        result = use_case.execute(1)
        
        assert result is not None
        assert result['movie']['title'] == 'Test Movie'
    
    def test_execute_not_found(self):
        """Test de película no encontrada"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        use_case = StreamMovieUseCase(movie_repo, progress_repo)
        result = use_case.execute(999)
        
        assert result is None


class TestTrackProgressUseCase:
    """Tests para TrackProgressUseCase"""
    
    def test_update_position_new(self):
        """Test de actualizar posición - nuevo registro"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        use_case = TrackProgressUseCase(progress_repo, movie_repo)
        result = use_case.update_position(
            user_id=1,
            media_type='movie',
            media_id=1,
            position=1800,
            duration=5400
        )
        
        assert result['position'] == 1800
        assert result['duration'] == 5400
    
    def test_update_position_existing(self):
        """Test de actualizar posición - registro existente"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        # Crear registro inicial
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 1,
            'position': 1000,
            'duration': 5400
        })
        
        use_case = TrackProgressUseCase(progress_repo, movie_repo)
        result = use_case.update_position(
            user_id=1,
            media_type='movie',
            media_id=1,
            position=2000,
            duration=5400
        )
        
        assert result['position'] == 2000
    
    def test_mark_completed(self):
        """Test de marcar como completado"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        # Crear registro
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 1,
            'position': 1000,
            'duration': 5400,
            'is_completed': False
        })
        
        use_case = TrackProgressUseCase(progress_repo, movie_repo)
        result = use_case.mark_completed(
            user_id=1,
            media_type='movie',
            media_id=1
        )
        
        assert result['is_completed'] is True
    
    def test_get_progress(self):
        """Test de obtener progreso"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        # Crear registro
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 1,
            'position': 1800,
            'duration': 5400
        })
        
        use_case = TrackProgressUseCase(progress_repo, movie_repo)
        result = use_case.get_progress(user_id=1, media_type='movie', media_id=1)
        
        assert result is not None
        assert result['position'] == 1800


class TestGetContinueWatchingUseCase:
    """Tests para GetContinueWatchingUseCase"""
    
    def test_get_continue_watching(self):
        """Test de obtener continuar viendo"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        # Crear registros de progreso
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 1,
            'position': 1800,
            'duration': 5400,
            'is_completed': False
        })
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 2,
            'position': 5000,
            'duration': 5400,
            'is_completed': True
        })
        
        use_case = GetContinueWatchingUseCase(progress_repo, movie_repo)
        result = use_case.execute(user_id=1, limit=10)
        
        assert len(result) == 1
        assert result[0]['progress']['media_id'] == 1


class TestGetWatchedContentUseCase:
    """Tests para GetWatchedContentUseCase"""
    
    def test_get_watched_content(self):
        """Test de obtener contenido visto"""
        movie_repo = MockMovieRepository()
        progress_repo = MockProgressRepository()
        
        # Crear registros
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 1,
            'position': 5400,
            'duration': 5400,
            'is_completed': True
        })
        progress_repo.save({
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 2,
            'position': 1800,
            'duration': 5400,
            'is_completed': False
        })
        
        use_case = GetWatchedContentUseCase(progress_repo, movie_repo)
        result = use_case.execute(user_id=1, limit=20)
        
        assert len(result) == 1
        assert result[0]['progress']['is_completed'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
