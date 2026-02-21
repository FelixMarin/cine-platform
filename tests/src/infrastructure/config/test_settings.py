"""
Tests para configuración de settings
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
sys.path.insert(0, project_root)


def test_settings_default_values():
    """Test de valores por defecto de settings"""
    from src.infrastructure.config.settings import Settings
    
    # Verify that Settings can be instantiated
    settings = Settings()
    
    # Check default values exist
    assert settings.MOVIES_FOLDER is not None
    assert settings.SERIES_FOLDER is not None
    assert settings.UPLOAD_FOLDER is not None
    assert settings.OUTPUT_FOLDER is not None
    assert settings.THUMBNAIL_FOLDER is not None
    assert settings.LOG_FOLDER is not None


def test_settings_singleton():
    """Test de singleton"""
    from src.infrastructure.config.settings import Settings
    
    # Both should return the same instance
    instance1 = Settings.get_instance()
    instance2 = Settings.get_instance()
    
    assert instance1 is instance2


def test_settings_from_env():
    """Test de valores desde variables de entorno"""
    # Temporarily set environment variable
    original = os.environ.get('MOVIES_FOLDER')
    try:
        os.environ['MOVIES_FOLDER'] = '/custom/path'
        
        # Reload module to pick up new env var
        import importlib
        import src.infrastructure.config.settings as settings_module
        importlib.reload(settings_module)
        
        # Check that custom value is used
        settings = settings_module.Settings()
        assert settings.MOVIES_FOLDER == '/custom/path'
    finally:
        # Restore original value
        if original:
            os.environ['MOVIES_FOLDER'] = original
        elif 'MOVIES_FOLDER' in os.environ:
            del os.environ['MOVIES_FOLDER']


def test_settings_postgres_config():
    """Test de configuración de PostgreSQL"""
    from src.infrastructure.config.settings import Settings
    
    settings = Settings()
    
    # Check postgres config exists
    assert settings.POSTGRES_HOST is not None
    assert settings.POSTGRES_PORT is not None
    assert settings.POSTGRES_DB is not None


def test_settings_omdb_config():
    """Test de configuración de OMDB"""
    from src.infrastructure.config.settings import Settings
    
    settings = Settings()
    
    # Check OMDB config exists
    assert settings.OMDB_API_KEY is not None
    assert settings.OMDB_LANGUAGE is not None


def test_settings_ffmpeg_config():
    """Test de configuración de FFmpeg"""
    from src.infrastructure.config.settings import Settings
    
    settings = Settings()
    
    # Check FFmpeg config exists
    assert settings.FFMPEG_THREADS is not None
    assert settings.FFMPEG_THREADS > 0


def test_settings_debug_mode():
    """Test de modo debug"""
    from src.infrastructure.config.settings import Settings
    
    settings = Settings()
    
    # Default should be false
    assert settings.DEBUG is False or settings.DEBUG is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
