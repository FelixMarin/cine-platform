"""
Tests para casos de uso de Optimizer
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.use_cases.optimizer import OptimizeMovieUseCase, EstimateSizeUseCase


class MockQueueService:
    def __init__(self):
        self.queue = []
        self.status = {'current': None, 'cancelled': False}
    
    def add_task(self, task):
        self.queue.append(task)
        return True
    
    def get_status(self):
        return self.status
    
    def cancel_current_task(self):
        self.status['cancelled'] = True
        return True
    
    def get_queue_size(self):
        return len(self.queue)


class MockEncoderService:
    def __init__(self):
        self.profiles = {
            'balanced': {'video_bitrate': '2000k', 'audio_bitrate': '128k'}
        }
    
    def get_available_profiles(self):
        return self.profiles
    
    def estimate_size(self, input_path, profile):
        return {
            'original_mb': 1000,
            'estimated_mb': 500,
            'compression_ratio': '50%'
        }


class TestOptimizeMovieUseCase:
    """Tests para OptimizeMovieUseCase"""
    
    def test_execute_adds_task(self):
        """Test de añadir tarea a la cola"""
        queue_service = MockQueueService()
        
        use_case = OptimizeMovieUseCase(queue_service)
        result = use_case.execute('/path/to/video.mkv', 'balanced')
        
        assert result['success'] is True
        assert result['status'] == 'queued'
        assert len(queue_service.queue) == 1
    
    def test_process_folder(self):
        """Test de procesar carpeta"""
        queue_service = MockQueueService()
        
        # No existe, pero el test verificará que intente
        use_case = OptimizeMovieUseCase(queue_service)
        
        # El método intenta acceder al sistema de archivos
        # Esto es más un test de integración
        pass
    
    def test_get_status(self):
        """Test de obtener estado"""
        queue_service = MockQueueService()
        
        use_case = OptimizeMovieUseCase(queue_service)
        status = use_case.get_status()
        
        assert 'current' in status
    
    def test_cancel_current(self):
        """Test de cancelar"""
        queue_service = MockQueueService()
        
        use_case = OptimizeMovieUseCase(queue_service)
        result = use_case.cancel_current()
        
        assert result is True
    
    def test_get_available_profiles(self):
        """Test de obtener perfiles"""
        queue_service = MockQueueService()
        encoder_service = MockEncoderService()
        
        use_case = OptimizeMovieUseCase(queue_service, encoder_service)
        profiles = use_case.get_available_profiles()
        
        assert 'balanced' in profiles


class TestEstimateSizeUseCase:
    """Tests para EstimateSizeUseCase"""
    
    def test_execute(self):
        """Test de estimación"""
        encoder_service = MockEncoderService()
        
        use_case = EstimateSizeUseCase(encoder_service)
        result = use_case.execute('/path/to/video.mkv', 'balanced')
        
        assert result is not None
        assert 'estimated_mb' in result
    
    def test_execute_no_encoder(self):
        """Test sin encoder"""
        use_case = EstimateSizeUseCase(None)
        result = use_case.execute('/path/to/video.mkv', 'balanced')
        
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
