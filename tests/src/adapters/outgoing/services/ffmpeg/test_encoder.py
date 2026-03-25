"""
Tests para el servicio de encoder de FFmpeg
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.services.ffmpeg.encoder import FFmpegEncoderService


class TestFFmpegEncoderService:
    """Tests del servicio de encoder de FFmpeg"""
    
    def test_encoder_service_initialization_default(self):
        """Test de inicialización con valores por defecto"""
        encoder = FFmpegEncoderService()
        
        assert encoder is not None
        assert encoder._current_profile == "balanced"
    
    def test_encoder_service_initialization_with_env(self):
        """Test de inicialización con variable de entorno"""
        with patch.dict(os.environ, {"FFMPEG_API_URL": "http://custom:9090"}):
            encoder = FFmpegEncoderService()
            
            assert encoder.api_url == "http://custom:9090"
    
    def test_check_health_success(self):
        """Test de verificación de salud exitosa"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = encoder.check_health()
            
            assert result is True
    
    def test_check_health_failure(self):
        """Test de verificación de salud fallida"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            result = encoder.check_health()
            
            assert result is False
    
    def test_check_health_exception(self):
        """Test de verificación de salud con excepción"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get', side_effect=Exception("Connection error")):
            result = encoder.check_health()
            
            assert result is False
    
    def test_get_gpu_available_success(self):
        """Test de verificación de GPU disponible"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"gpu_available": True}
            mock_get.return_value = mock_response
            
            result = encoder.get_gpu_available()
            
            assert result is True
    
    def test_get_gpu_available_not_available(self):
        """Test de verificación de GPU no disponible"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"gpu_available": False}
            mock_get.return_value = mock_response
            
            result = encoder.get_gpu_available()
            
            assert result is False
    
    def test_get_gpu_available_exception(self):
        """Test de verificación de GPU con excepción"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get', side_effect=Exception("Error")):
            result = encoder.get_gpu_available()
            
            assert result is False
    
    def test_run_probe_api_success(self):
        """Test de probe de API exitoso"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"duration": 7200}
            mock_get.return_value = mock_response
            
            result = encoder._run_probe_api("/path/to/video.mkv")
            
            assert result == {"duration": 7200}
    
    def test_run_probe_api_failure(self):
        """Test de probe de API fallido"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = encoder._run_probe_api("/nonexistent/video.mkv")
            
            assert result is None
    
    def test_run_probe_api_exception(self):
        """Test de probe de API con excepción"""
        encoder = FFmpegEncoderService()
        
        with patch('requests.get', side_effect=Exception("Network error")):
            result = encoder._run_probe_api("/path/video.mkv")
            
            assert result is None


class TestFFmpegEncoderServiceInterface:
    """Tests de implementación de la interfaz IEncoderService"""
    
    def test_implements_interface(self):
        """Test de que implementa la interfaz IEncoderService"""
        encoder = FFmpegEncoderService()
        
        # Verificar que tiene los métodos de la interfaz
        assert hasattr(encoder, 'check_health')
        assert hasattr(encoder, 'get_gpu_available')
    
    def test_current_profile(self):
        """Test del perfil actual"""
        encoder = FFmpegEncoderService()
        
        assert encoder._current_profile == "balanced"