"""
Configuración de pytest para los tests de la nueva arquitectura
"""
import pytest
import sys
import os

# Añadir el path del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)


@pytest.fixture
def temp_video_file(tmp_path):
    """Fixture para crear un archivo de video temporal"""
    video_path = tmp_path / "test_video.mkv"
    video_path.write_bytes(b"test video content")
    return str(video_path)


@pytest.fixture
def mock_movie_data():
    """Fixture con datos de película de prueba"""
    return {
        'id': 1,
        'title': 'Test Movie',
        'year': 2023,
        'path': '/path/to/movie.mkv',
        'size': 1000000000,
        'duration': 5400,
        'genre': 'Action',
        'is_optimized': False,
        'thumbnail': '/path/to/thumb.jpg'
    }


@pytest.fixture
def mock_progress_data():
    """Fixture con datos de progreso de prueba"""
    return {
        'user_id': 1,
        'media_type': 'movie',
        'media_id': 1,
        'position': 1800,
        'duration': 5400,
        'is_completed': False,
        'watch_count': 1
    }


@pytest.fixture
def mock_user_data():
    """Fixture con datos de usuario de prueba"""
    return {
        'id': 1,
        'email': 'test@example.com',
        'username': 'testuser',
        'role': 'user',
        'is_active': True
    }
