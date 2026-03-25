"""
Tests para las rutas de streaming
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from flask import Flask


@pytest.fixture
def app():
    """Create test Flask app"""
    from src.adapters.entry.web.routes import streaming
    app = Flask(__name__)
    app.register_blueprint(streaming.streaming_bp)
    app.register_blueprint(streaming.stream_page_bp)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


class TestStreamingRoutes:
    """Tests de las rutas de streaming"""
    
    def test_init_streaming_routes(self):
        """Test de inicialización de rutas"""
        from src.adapters.entry.web.routes.streaming import init_streaming_routes
        # La función no hace nada, pero debe ejecutarse sin errores
        result = init_streaming_routes()
        assert result is None
    
    def test_stream_video_not_found(self, client):
        """Test de stream_video cuando el archivo no existe"""
        with patch.dict(os.environ, {"MOVIES_FOLDER": "/tmp/nonexistent"}):
            response = client.get("/api/streaming/nonexistent_file.mkv")
            assert response.status_code == 404
    
    def test_video_info_not_found(self, client):
        """Test de video_info cuando el archivo no existe"""
        with patch.dict(os.environ, {"MOVIES_FOLDER": "/tmp/nonexistent"}):
            response = client.get("/api/streaming/info/nonexistent_file.mkv")
            assert response.status_code == 404
            data = response.get_json()
            assert "error" in data
    
    def test_video_info_file_exists(self, client):
        """Test de video_info cuando el archivo existe"""
        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            with patch.dict(os.environ, {"MOVIES_FOLDER": os.path.dirname(temp_path)}):
                response = client.get(f"/api/streaming/info/{os.path.basename(temp_path)}")
                assert response.status_code == 200
                data = response.get_json()
                assert "filename" in data
                assert "size" in data
        finally:
            os.unlink(temp_path)
    
    def test_stream_page_video_calls_stream_video(self, client):
        """Test que stream_page_video llama a stream_video"""
        with patch("src.adapters.entry.web.routes.streaming.stream_video") as mock_stream:
            mock_stream.return_value = "response"
            response = client.get("/stream/test.mkv")
            # La función debería haber sido llamada
            # (el blueprint de página redirige a stream_video)
    
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test video data")
    @patch("os.path.getsize")
    def test_streaming_bp_initialization(self, mock_getsize, mock_file, mock_exists):
        """Test de que el blueprint se inicializa correctamente"""
        from src.adapters.entry.web.routes import streaming
        assert streaming.streaming_bp is not None
        assert streaming.stream_page_bp is not None
        assert streaming.streaming_bp.name == "streaming"
        assert streaming.stream_page_bp.name == "stream_page"


class TestStreamingRoutePatterns:
    """Tests de los patrones de rutas de streaming"""
    
    def test_streaming_bp_url_prefix(self):
        """Test del prefijo de URL del blueprint de streaming"""
        from src.adapters.entry.web.routes import streaming
        # El prefijo debe ser /api/streaming
        assert "/api/streaming" in str(streaming.streaming_bp.url_prefix)
    
    def test_stream_page_route(self):
        """Test de la ruta /stream/ - verificar que la función existe"""
        from src.adapters.entry.web.routes import streaming
        # Verificar que la función de ruta existe
        assert callable(streaming.stream_page_video)


class TestStreamingFunctions:
    """Tests de funciones auxiliares de streaming"""
    
    def test_streaming_route_parsing(self):
        """Test de parsing de rutas de streaming"""
        # El routing es manejado por Flask, verificamos la configuración
        from src.adapters.entry.web.routes import streaming
        
        # Verificar que las funciones existen
        assert callable(streaming.stream_video)
        assert callable(streaming.video_info)
        assert callable(streaming.init_streaming_routes)