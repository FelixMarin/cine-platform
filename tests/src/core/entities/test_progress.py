"""
Tests para la entidad Progress
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.entities.progress import Progress, MediaType


class TestProgressEntity:
    """Tests para la entidad Progress"""
    
    def test_create_progress_basic(self):
        """Test de creación básica"""
        progress = Progress(
            user_id=1,
            media_type=MediaType.MOVIE,
            media_id=1,
            position=1800,  # 30 minutos
            duration=5400   # 90 minutos
        )
        
        assert progress.user_id == 1
        assert progress.media_type == MediaType.MOVIE
        assert progress.media_id == 1
        assert progress.position == 1800
        assert progress.duration == 5400
    
    def test_progress_percentage(self):
        """Test de porcentaje de reproducción"""
        progress = Progress(
            user_id=1,
            media_type=MediaType.MOVIE,
            media_id=1,
            position=2700,
            duration=5400
        )
        
        assert progress.percentage == 50.0
        
        # 0%
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=0, duration=5400)
        assert progress.percentage == 0.0
        
        # 100%
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=5400, duration=5400)
        assert progress.percentage == 100.0
    
    def test_position_formatted(self):
        """Test de posición formateada"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=3661, duration=5400)
        assert progress.position_formatted == "01:01:01"
    
    def test_duration_formatted(self):
        """Test de duración formateada"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=0, duration=5400)
        assert progress.duration_formatted == "01:30:00"
    
    def test_remaining_time(self):
        """Test de tiempo restante"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=1800, duration=5400)
        assert progress.remaining_time == 3600
    
    def test_update_position(self):
        """Test de actualización de posición"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=0, duration=5400)
        progress.update_position(2000)
        
        assert progress.position == 2000
        assert progress.is_completed is False
        
        # Más del 90% debería marcar como completado
        progress.update_position(5000)
        assert progress.is_completed is True
    
    def test_mark_completed(self):
        """Test de marcar como completado"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=1000, duration=5400)
        progress.mark_completed()
        
        assert progress.is_completed is True
        assert progress.position == progress.duration
    
    def test_increment_watch_count(self):
        """Test de incremento de contador"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=0, duration=5400)
        assert progress.watch_count == 0
        
        progress.increment_watch_count()
        assert progress.watch_count == 1
        
        progress.increment_watch_count()
        assert progress.watch_count == 2
    
    def test_to_dict(self):
        """Test de conversión a diccionario"""
        progress = Progress(
            user_id=1,
            media_type=MediaType.MOVIE,
            media_id=1,
            position=1800,
            duration=5400
        )
        
        data = progress.to_dict()
        
        assert data['user_id'] == 1
        assert data['media_type'] == 'movie'
        assert data['media_id'] == 1
        assert data['position'] == 1800
        assert 'percentage' in data
        assert 'position_formatted' in data
    
    def test_from_dict(self):
        """Test de creación desde diccionario"""
        data = {
            'user_id': 1,
            'media_type': 'movie',
            'media_id': 1,
            'position': 1800,
            'duration': 5400
        }
        
        progress = Progress.from_dict(data)
        
        assert progress.user_id == 1
        assert progress.media_type == MediaType.MOVIE
    
    def test_episode_type(self):
        """Test con tipo Episode"""
        progress = Progress(user_id=1, media_type=MediaType.EPISODE, media_id=5, position=1800, duration=2700)
        
        assert progress.media_type == MediaType.EPISODE
        assert progress.duration == 2700


class TestProgressEdgeCases:
    """Tests para casos extremos"""
    
    def test_zero_duration(self):
        """Test con duración cero"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=0, duration=0)
        assert progress.percentage == 0
        assert progress.remaining_time == 0
    
    def test_position_exceeds_duration(self):
        """Test cuando posición excede duración"""
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=6000, duration=5400)
        assert progress.percentage == 100
    
    def test_completed_threshold(self):
        """Test del umbral de completado"""
        # 89% - no completado
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=4806, duration=5400)
        assert progress.is_completed is False
        
        # 90% - должен быть завершен
        progress = Progress(user_id=1, media_type=MediaType.MOVIE, media_id=1, position=0, duration=5400)
        progress.update_position(4861)  # 90.01%
        assert progress.is_completed is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
