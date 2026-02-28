"""
Tests para OMDB Metadata Service
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.adapters.outgoing.services.omdb.client import OMDBMetadataService


class TestOMDBMetadataService:
    """Tests para OMDBMetadataService"""
    
    def test_init_with_api_key(self):
        """Test de inicialización con API key"""
        service = OMDBMetadataService(api_key="test_key")
        
        assert service._api_key == "test_key"
        assert service._language == 'es'
    
    def test_init_with_env_variable(self):
        """Test de inicialización con variable de entorno"""
        with patch.dict(os.environ, {'OMDB_API_KEY': 'env_key'}):
            service = OMDBMetadataService()
            
            assert service._api_key == 'env_key'
    
    def test_is_available_with_key(self):
        """Test de disponibilidad con clave"""
        service = OMDBMetadataService(api_key="test_key")
        
        assert service.is_available() is True
    
    def test_omdb_service_basic(self):
        """Test básico del servicio OMDB"""
        service = OMDBMetadataService()
        assert service is not None
    
    @patch('requests.Session.get')
    def test_get_movie_metadata_success(self, mock_get):
        """Test de obtener metadatos - éxito"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'Title': 'Test Movie',
            'Year': '2023',
            'Plot': 'A test plot',
            'Poster': 'http://test.com/poster.jpg',
            'Response': 'True'
        }
        mock_get.return_value = mock_response
        
        service = OMDBMetadataService(api_key="test_key")
        result = service.get_movie_metadata("Test Movie")
        
        assert result is not None
        assert result['Title'] == 'Test Movie'
    
    @patch('requests.Session.get')
    def test_get_movie_metadata_not_found(self, mock_get):
        """Test de obtener metadatos - no encontrado"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'Response': 'False',
            'Error': 'Movie not found!'
        }
        mock_get.return_value = mock_response
        
        service = OMDBMetadataService(api_key="test_key")
        result = service.get_movie_metadata("Nonexistent Movie")
        
        assert result is None
    
    def test_get_movie_metadata_no_api_key(self):
        """Test sin API key"""
        service = OMDBMetadataService(api_key=None)
        result = service.get_movie_metadata("Test Movie")
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_search_movies(self, mock_get):
        """Test de búsqueda"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'Search': [
                {'Title': 'Test 1', 'Year': '2023'},
                {'Title': 'Test 2', 'Year': '2022'}
            ],
            'Response': 'True'
        }
        mock_get.return_value = mock_response
        
        service = OMDBMetadataService(api_key="test_key")
        results = service.search_movies("Test")
        
        assert len(results) == 2
    
    @patch('requests.Session.get')
    def test_get_poster_url(self, mock_get):
        """Test de obtener URL del póster"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'Title': 'Test Movie',
            'Poster': 'http://test.com/poster.jpg',
            'Response': 'True'
        }
        mock_get.return_value = mock_response
        
        service = OMDBMetadataService(api_key="test_key")
        url = service.get_poster_url("Test Movie")
        
        assert url is not None
        assert '/proxy-image' in url
    
    @patch('requests.Session.get')
    def test_get_poster_url_not_found(self, mock_get):
        """Test de póster no encontrado"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'Title': 'Test Movie',
            'Poster': 'N/A',
            'Response': 'True'
        }
        mock_get.return_value = mock_response
        
        service = OMDBMetadataService(api_key="test_key")
        url = service.get_poster_url("Test Movie")
        
        assert url is None
    
    def test_get_serie_metadata(self):
        """Test de metadatos de serie"""
        with patch.object(service := OMDBMetadataService(api_key="test_key"), '_make_request') as mock:
            mock.return_value = {
                'Title': 'Test Serie',
                'Type': 'series',
                'Response': 'True'
            }
            
            result = service.get_serie_metadata("Test Serie")
            
            assert result is not None


class TestOMDBErrorHandling:
    """Tests de manejo de errores"""
    
    @patch('requests.Session.get')
    def test_network_error(self, mock_get):
        """Test de error de red"""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        
        service = OMDBMetadataService(api_key="test_key")
        result = service.get_movie_metadata("Test")
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_invalid_json(self, mock_get):
        """Test de JSON inválido"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        service = OMDBMetadataService(api_key="test_key")
        result = service.get_movie_metadata("Test")
        
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
