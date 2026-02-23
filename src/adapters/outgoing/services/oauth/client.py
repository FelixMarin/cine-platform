"""
Cliente OAuth2 para autenticación
Implementa el flujo Authorization Code + PKCE
"""
import os
import base64
import secrets
import hashlib
import requests
from typing import Tuple, Dict, Optional


class OAuth2Client:
    """Cliente OAuth2 para autenticación de usuarios"""
    
    def __init__(self):
        """Inicializa el cliente OAuth2 con las credenciales del entorno"""
        self.base_url = os.environ.get("OAUTH2_URL", "http://localhost:8080").rstrip('/')
        self.client_id = os.environ.get("OAUTH2_CLIENT_ID", "cine-platform")
        self.client_secret = os.environ.get("OAUTH2_CLIENT_SECRET", "cine-platform-secret")
        
        # Endpoints
        self.token_endpoint = os.environ.get("OAUTH2_TOKEN_ENDPOINT", "/oauth2/token")
        self.authorize_endpoint = os.environ.get("OAUTH2_AUTHORIZE_ENDPOINT", "/oauth2/authorize")
        self.userinfo_endpoint = os.environ.get("OAUTH2_USERINFO_ENDPOINT", "/userinfo")
        self.revoke_endpoint = os.environ.get("OAUTH2_REVOKE_ENDPOINT", "/oauth2/revoke")
        
        # Redirect URI
        self.redirect_uri = os.environ.get("OAUTH2_REDIRECT_URI", "http://localhost:5000/oauth/callback")
        
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_data: Optional[Dict] = None
    
    def _get_basic_auth_header(self) -> Dict[str, str]:
        """Genera el header de Basic Auth"""
        raw = f"{self.client_id}:{self.client_secret}".encode()
        encoded = base64.b64encode(raw).decode()
        return {"Authorization": f"Basic {encoded}"}
    
    def generate_code_verifier(self) -> str:
        """Genera un code_verifier aleatorio (43-128 caracteres)"""
        # Generar 32 bytes aleatorios y codificar en base64url
        random_bytes = secrets.token_bytes(32)
        verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        return verifier
    
    def generate_code_challenge(self, code_verifier: str) -> str:
        """Genera un code_challenge a partir del code_verifier usando SHA-256"""
        # SHA-256 hash del verifier
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return challenge
    
    def get_authorization_url(self, code_verifier: str, state: str = "") -> str:
        """
        Genera la URL de autorización con PKCE
        
        Args:
            code_verifier: El code_verifier generado localmente
            state: Estado para prevenir CSRF
            
        Returns:
            URL de autorización completa
        """
        code_challenge = self.generate_code_challenge(code_verifier)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid profile read write",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        
        if state:
            params["state"] = state
        
        from urllib.parse import urlencode
        return f"{self.base_url}{self.authorize_endpoint}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str, code_verifier: str) -> Tuple[bool, Dict]:
        """
        Intercambia código de autorización por token
        
        Args:
            code: El código de autorización recibido
            code_verifier: El code_verifier original generado
            
        Returns:
            Tupla (success, token_data)
        """
        url = f"{self.base_url}{self.token_endpoint}"
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
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
                self.refresh_token = data.get("refresh_token")
                return True, data
            else:
                return False, {"error": response.text, "status": response.status_code}
                
        except requests.exceptions.ConnectionError:
            return False, {"error": "Servidor OAuth no disponible"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def refresh_access_token(self, refresh_token: str = None) -> Tuple[bool, Dict]:
        """
        Refresca el token de acceso
        
        Args:
            refresh_token: Token de refresco (si no se usa el guardado)
            
        Returns:
            Tupla (success, token_data)
        """
        token = refresh_token or self.refresh_token
        if not token:
            return False, {"error": "No hay refresh_token disponible"}
        
        url = f"{self.base_url}{self.token_endpoint}"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": token,
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
                if data.get("refresh_token"):
                    self.refresh_token = data.get("refresh_token")
                return True, data
            else:
                return False, {"error": response.text}
                
        except Exception as e:
            return False, {"error": str(e)}
    
    def revoke_token(self, token: str = None) -> bool:
        """
        Revoca un token
        
        Args:
            token: Token a revocar (si no se usa el actual)
            
        Returns:
            True si se revocó correctamente
        """
        tok = token or self.token
        if not tok:
            return False
        
        url = f"{self.base_url}{self.revoke_endpoint}"
        
        try:
            response = requests.post(
                url,
                data={"token": tok},
                headers=self._get_basic_auth_header(),
                timeout=10
            )
            return response.status_code in (200, 204)
        except Exception:
            return False
    
    def get_userinfo(self, token: str = None) -> Optional[Dict]:
        """
        Obtiene información del usuario
        
        Args:
            token: Token a usar (si no se usa el actual)
            
        Returns:
            Datos del usuario o None
        """
        tok = token or self.token
        if not tok:
            return None
        
        url = f"{self.base_url}{self.userinfo_endpoint}"
        
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {tok}"},
                timeout=10
            )
            
            if response.status_code == 200:
                self.user_data = response.json()
                return self.user_data
            return None
        except Exception:
            return None
    
    # Métodos de compatibilidad con el código anterior
    def login(self, username: str, password: str) -> Tuple[bool, Dict]:
        """
        Autentica al usuario usando OAuth2 Password Grant
        OBSOLETO: Usar get_authorization_url + exchange_code_for_token
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
            return False, {"error": "Servidor OAuth no disponible"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica un token de acceso"""
        return self.get_userinfo(token)
