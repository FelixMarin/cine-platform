"""
Tests para configuración de dependencias
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.adapters.config import dependencies


class TestDependencies:
    """Tests para el sistema de inyección de dependencias"""
    
    def test_get_database_connection_returns_none(self):
        """Test de obtener conexión a DB"""
        conn = dependencies.get_database_connection()
        
        assert conn is None  # Sin implementación real
    
    def test_init_repositories_with_filesystem(self):
        """Test de inicialización con filesystem"""
        # Guardar estado original
        original_movie_repo = dependencies._movie_repository
        
        dependencies.init_repositories(use_postgresql=False)
        
        # Verificar que se inicializó
        assert dependencies._movie_repository is not None
        
        # Restaurar
        dependencies._movie_repository = original_movie_repo
    
    def test_init_repositories_with_postgresql(self):
        """Test de inicialización con PostgreSQL"""
        original_movie_repo = dependencies._movie_repository
        original_progress_repo = dependencies._progress_repository
        
        dependencies.init_repositories(use_postgresql=True)
        
        # Verificar que se inicializó
        assert dependencies._movie_repository is not None
        
        # Restaurar
        dependencies._movie_repository = original_movie_repo
        dependencies._progress_repository = original_progress_repo
    
    @patch('src.adapters.config.dependencies.OAuth2Client')
    def test_init_services(self, mock_oauth):
        """Test de inicialización de servicios"""
        # Configurar el mock de OAuth2Client para que no falle
        mock_oauth_instance = MagicMock()
        mock_oauth.return_value = mock_oauth_instance
        
        original_metadata = dependencies._metadata_service
        original_encoder = dependencies._encoder_service
        original_oauth = dependencies._oauth_service
        
        dependencies.init_services()
        
        # Verificar que se inicializó
        assert dependencies._metadata_service is not None
        assert dependencies._encoder_service is not None
        
        # Restaurar
        dependencies._metadata_service = original_metadata
        dependencies._encoder_service = original_encoder
        dependencies._oauth_service = original_oauth
    
    @patch('src.adapters.config.dependencies.OAuth2Client')
    def test_init_use_cases(self, mock_oauth):
        """Test de inicialización de casos de uso"""
        # Configurar el mock de OAuth2Client para que no falle
        mock_oauth_instance = MagicMock()
        mock_oauth.return_value = mock_oauth_instance
        
        # Primero inicializar repositorios y servicios
        original_movie_repo = dependencies._movie_repository
        dependencies.init_repositories(use_postgresql=False)
        dependencies.init_services()
        
        original_use_case = dependencies._list_movies_use_case
        
        dependencies.init_use_cases()
        
        # Verificar que se inicializó
        assert dependencies._list_movies_use_case is not None
        
        # Restaurar
        dependencies._list_movies_use_case = original_use_case
        dependencies._movie_repository = original_movie_repo
    
    @patch('src.adapters.config.dependencies.OAuth2Client')
    def test_init_all(self, mock_oauth):
        """Test de inicialización completa"""
        # Configurar el mock de OAuth2Client para que no falle
        mock_oauth_instance = MagicMock()
        mock_oauth.return_value = mock_oauth_instance
        
        original_movie_repo = dependencies._movie_repository
        original_progress_repo = dependencies._progress_repository
        original_metadata = dependencies._metadata_service
        original_encoder = dependencies._encoder_service
        original_oauth = dependencies._oauth_service
        original_use_cases = [
            dependencies._list_movies_use_case,
            dependencies._track_progress_use_case,
            dependencies._get_continue_watching_use_case,
        ]
        
        # Inicializar
        dependencies.init_all(use_postgresql=False)
        
        # Verificaciones
        assert dependencies._movie_repository is not None
        assert dependencies._progress_repository is not None
        assert dependencies._metadata_service is not None
        assert dependencies._encoder_service is not None
        
        # Restaurar estado original
        dependencies._movie_repository = original_movie_repo
        dependencies._progress_repository = original_progress_repo
        dependencies._metadata_service = original_metadata
        dependencies._encoder_service = original_encoder
        dependencies._oauth_service = original_oauth
        for i, use_case in enumerate(original_use_cases):
            if i == 0:
                dependencies._list_movies_use_case = use_case
            elif i == 1:
                dependencies._track_progress_use_case = use_case
            elif i == 2:
                dependencies._get_continue_watching_use_case = use_case
    
    def test_get_movie_repository(self):
        """Test de getter de repositorio"""
        original = dependencies._movie_repository
        
        dependencies._movie_repository = "test_repo"
        
        result = dependencies.get_movie_repository()
        
        assert result == "test_repo"
        
        dependencies._movie_repository = original
    
    def test_get_progress_repository(self):
        """Test de getter de progreso"""
        original = dependencies._progress_repository
        
        dependencies._progress_repository = "test_progress"
        
        result = dependencies.get_progress_repository()
        
        assert result == "test_progress"
        
        dependencies._progress_repository = original
    
    def test_get_metadata_service(self):
        """Test de getter de servicio de metadatos"""
        original = dependencies._metadata_service
        
        dependencies._metadata_service = "test_metadata"
        
        result = dependencies.get_metadata_service()
        
        assert result == "test_metadata"
        
        dependencies._metadata_service = original
    
    def test_get_encoder_service(self):
        """Test de getter de servicio de encoder"""
        original = dependencies._encoder_service
        
        dependencies._encoder_service = "test_encoder"
        
        result = dependencies.get_encoder_service()
        
        assert result == "test_encoder"
        
        dependencies._encoder_service = original


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
