import pytest
import sys
import os
import queue
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def setup_environment(monkeypatch):
    """Configurar entorno para tests"""
    
    # Variables de entorno necesarias
    os.environ.setdefault('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
    os.environ.setdefault('SERIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual/series')
    os.environ.setdefault('UPLOAD_FOLDER', '/tmp/cineplatform/uploads')
    os.environ.setdefault('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    os.environ.setdefault('THUMBNAIL_FOLDER', '/tmp/cineplatform/thumbnails')
    os.environ.setdefault('LOG_FOLDER', '/tmp/cineplatform/logs')
    os.environ.setdefault('POSTGRES_HOST', 'localhost')
    os.environ.setdefault('POSTGRES_PORT', '5432')
    os.environ.setdefault('POSTGRES_DB', 'cineplatform')
    os.environ.setdefault('POSTGRES_USER', 'postgres')
    os.environ.setdefault('POSTGRES_PASSWORD', '')
    os.environ.setdefault('OMDB_API_KEY', '')
    os.environ.setdefault('OMDB_LANGUAGE', 'es')
    os.environ.setdefault('OAUTH2_URL', 'http://localhost')
    os.environ.setdefault('OAUTH2_CLIENT_ID', 'test')
    os.environ.setdefault('OAUTH2_CLIENT_SECRET', 'test')
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('DEBUG', 'false')
    os.environ.setdefault('FFMPEG_THREADS', '4')
    os.environ.setdefault('USE_POSTGRESQL', 'false')
    os.environ.setdefault('MAX_CONTENT_LENGTH', '100000000')
    os.environ.setdefault('SESSION_COOKIE_DOMAIN', 'localhost')
    os.environ.setdefault('SESSION_COOKIE_HTTPONLY', 'true')
    os.environ.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    os.environ.setdefault('SESSION_COOKIE_SECURE', 'false')
    os.environ.setdefault('SESSION_COOKIE_PATH', '/')
    os.environ.setdefault('APP_ENV', 'development')
    
    return
