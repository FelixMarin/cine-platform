"""
Configuración de la aplicación
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    """Configuración centralizada de la aplicación"""
    
    # ============================
    # 📁 Rutas de archivos
    # ============================
    MOVIES_FOLDER: str = os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
    SERIES_FOLDER: str = os.environ.get('SERIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual/series')
    UPLOAD_FOLDER: str = os.environ.get('UPLOAD_FOLDER', '/tmp/cineplatform/uploads')
    OUTPUT_FOLDER: str = os.environ.get('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    THUMBNAIL_FOLDER: str = os.environ.get('THUMBNAIL_FOLDER', '/tmp/cineplatform/thumbnails')
    LOG_FOLDER: str = os.environ.get('LOG_FOLDER', '/tmp/cineplatform/logs')
    
    # ============================
    # 🗄️ PostgreSQL
    # ============================
    USE_POSTGRESQL: bool = os.environ.get('USE_POSTGRESQL', 'false').lower() == 'true'
    POSTGRES_HOST: str = os.environ.get('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT: int = int(os.environ.get('POSTGRES_PORT', '5432'))
    POSTGRES_DB: str = os.environ.get('POSTGRES_DB', 'cineplatform')
    POSTGRES_USER: str = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD: str = os.environ.get('POSTGRES_PASSWORD', '')
    
    # ============================
    # 🎬 OMDB (API de películas)
    # ============================
    OMDB_API_KEY: str = os.environ.get('OMDB_API_KEY', '')
    OMDB_LANGUAGE: str = os.environ.get('OMDB_LANGUAGE', 'es')
    
    # ============================
    # 🔐 OAuth2 - Comunicación INTERNA (backend-to-backend)
    # ============================
    OAUTH2_URL: str = os.environ.get('OAUTH2_URL', '')
    OAUTH2_CLIENT_ID: str = os.environ.get('OAUTH2_CLIENT_ID', '')
    OAUTH2_CLIENT_SECRET: str = os.environ.get('OAUTH2_CLIENT_SECRET', '')
    
    # ============================
    # 🌐 OAuth2 - URLs PÚBLICAS (para el navegador)
    # ============================
    PUBLIC_OAUTH2_URL: str = os.environ.get('PUBLIC_OAUTH2_URL', '')
    PUBLIC_REDIRECT_URI: str = os.environ.get('PUBLIC_REDIRECT_URI', '')
    
    # ============================
    # 📍 OAuth2 - Endpoints (desde ConfigMap)
    # ============================
    OAUTH2_AUTHORIZE_ENDPOINT: str = os.environ.get('OAUTH2_AUTHORIZE_ENDPOINT', '/oauth2/authorize')
    OAUTH2_TOKEN_ENDPOINT: str = os.environ.get('OAUTH2_TOKEN_ENDPOINT', '/oauth/token')
    OAUTH2_USERINFO_ENDPOINT: str = os.environ.get('OAUTH2_USERINFO_ENDPOINT', '/user/me')
    OAUTH2_REVOKE_ENDPOINT: str = os.environ.get('OAUTH2_REVOKE_ENDPOINT', '/oauth2/revoke')
    
    # ============================
    # 🔑 Seguridad
    # ============================
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # ============================
    # 📤 Configuración de upload
    # ============================
    MAX_CONTENT_LENGTH: int = int(os.environ.get('MAX_CONTENT_LENGTH', '100000000'))  # 100MB
    
    # ============================
    # 🍪 Cookies
    # ============================
    SESSION_COOKIE_DOMAIN: str = os.environ.get('SESSION_COOKIE_DOMAIN', 'localhost')
    SESSION_COOKIE_HTTPONLY: bool = os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE: str = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE: bool = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_PATH: str = os.environ.get('SESSION_COOKIE_PATH', '/')
    
    # ============================
    # 🎬 FFmpeg
    # ============================
    FFMPEG_THREADS: int = int(os.environ.get('FFMPEG_THREADS', '4'))
    
    # ============================
    # 🌍 Entorno
    # ============================
    APP_ENV: str = os.environ.get('APP_ENV', 'development')
    
    # ============================
    # Instancia singleton
    # ============================
    _instance: Optional['Settings'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'Settings':
        """Devuelve la instancia singleton de Settings"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_oauth_config_for_frontend(cls) -> dict:
        """Devuelve la configuración OAuth2 para el frontend"""
        return {
            'serverUrl': cls.PUBLIC_OAUTH2_URL,
            'clientId': cls.OAUTH2_CLIENT_ID,
            'redirectUri': cls.PUBLIC_REDIRECT_URI,
            'scopes': 'openid profile read write'
        }


# Instancia global de configuración
settings = Settings.get_instance()
