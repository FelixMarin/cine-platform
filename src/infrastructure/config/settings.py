"""
Configuración de la aplicación
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Configuración centralizada de la aplicación"""
    
    # ... (todo lo que ya tienes) ...
    
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
    
    # ... resto de tu configuración ...
    
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
settings = Settings()