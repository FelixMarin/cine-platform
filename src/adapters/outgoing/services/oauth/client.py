"""
Cliente OAuth2 para autenticación
Implementa el flujo Password Grant para autenticar usuarios
"""
import os
import base64
import requests
from typing import Tuple, Dict, Optional


class OAuth2Client:
    """Cliente OAuth2 para autenticación de usuarios"""
    
    def __init__(self):
        """Inicializa el cliente OAuth2 con las credenciales del entorno"""
        self.base_url = os.environ.get("OAUTH2_URL", "http://localhost:8080").rstrip('/')
        self.client_id = os.environ.get("OAUTH2_CLIENT_ID", "proveedor-oauth")
        self.client_secret = os.environ.get("OAUTH2_CLIENT_SECRET", "123456")
        
        # Endpoints
        self.token_endpoint = os.environ.get("OAUTH2_TOKEN_ENDPOINT", "/oauth/token")
        self.userinfo_endpoint = os.environ.get("OAUTH2_USERINFO_ENDPOINT", "/userinfo")
        
        self.token: Optional[str] = None
        self.user_data: Optional[Dict] = None
    
    def _get_basic_auth_header(self) -> Dict[str, str]:
        """Genera el header de Basic Auth"""
        raw = f"{self.client_id}:{self.client_secret}".encode()
        encoded = base64.b64encode(raw).decode()
        return {"Authorization": f"Basic {encoded}"}
    
    def login(self, username: str, password: str) -> Tuple[bool, Dict]:
        """
        Autentica al usuario usando OAuth2 Password Grant
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            Tupla (success, user_data)
        """
        url = f"{self.base_url}{self.token_endpoint}"
        
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(
                url, 
                data=payload, 
                headers=self._get_basic_auth_header(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_data = {"username": username}
                return True, self.user_data
            else:
                return False, {"error": response.text}
                
        except requests.exceptions.ConnectionError:
            # Servidor OAuth no disponible
            return False, {"error": "Servidor OAuth no disponible"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica un token de acceso"""
        if not token:
            return None
        
        url = f"{self.base_url}{self.userinfo_endpoint}"
        
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_authorization_url(self, redirect_uri: str, state: str = "") -> str:
        """Genera la URL de autorización para OAuth2 Authorization Code Grant"""
        authorize_endpoint = os.environ.get("OAUTH2_AUTHORIZE_ENDPOINT", "/authorize")
        url = f"{self.base_url}{authorize_endpoint}"
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state
        }
        
        # Añadir params a la URL
        from urllib.parse import urlencode
        return f"{url}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Tuple[bool, Dict]:
        """Intercambia código de autorización por token"""
        url = f"{self.base_url}{self.token_endpoint}"
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                return True, data
            return False, {"error": response.text}
        except Exception as e:
            return False, {"error": str(e)}
