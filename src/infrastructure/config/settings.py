"""
Configuración de la aplicación
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Configuración centralizada de la aplicación"""
    
    # Rutas
    MOVIES_FOLDER: str = os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
    SERIES_FOLDER: str = os.environ.get('SERIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual/series')
    UPLOAD_FOLDER: str = os.environ.get('UPLOAD_FOLDER', '/tmp/cineplatform/uploads')
    OUTPUT_FOLDER: str = os.environ.get('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    THUMBNAIL_FOLDER: str = os.environ.get('THUMBNAIL_FOLDER', '/tmp/cineplatform/thumbnails')
    LOG_FOLDER: str = os.environ.get('LOG_FOLDER', '/tmp/cineplatform/logs')
    
    # Base de datos PostgreSQL
    POSTGRES_HOST: str = os.environ.get('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT: int = int(os.environ.get('POSTGRES_PORT', '5432'))
    POSTGRES_DB: str = os.environ.get('POSTGRES_DB', 'cineplatform')
    POSTGRES_USER: str = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD: str = os.environ.get('POSTGRES_PASSWORD', '')
    
    # OMDB API
    OMDB_API_KEY: str = os.environ.get('OMDB_API_KEY', '')
    OMDB_LANGUAGE: str = os.environ.get('OMDB_LANGUAGE', 'es')
    
    # OAuth
    OAUTH2_URL: str = os.environ.get('OAUTH2_URL', '')
    OAUTH2_CLIENT_ID: str = os.environ.get('OAUTH2_CLIENT_ID', '')
    OAUTH2_CLIENT_SECRET: str = os.environ.get('OAUTH2_CLIENT_SECRET', '')
    
    # Aplicación
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # FFmpeg
    FFMPEG_THREADS: int = int(os.environ.get('FFMPEG_THREADS', '4'))
    
    # PostgreSQL disponible (para migración)
    USE_POSTGRESQL: bool = os.environ.get('USE_POSTGRESQL', 'false').lower() == 'true'
    
    @classmethod
    def get_instance(cls) -> 'Settings':
        """Obtiene la instancia singleton"""
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance


# Instancia global de configuración
settings = Settings.get_instance()
