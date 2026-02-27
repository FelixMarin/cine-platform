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

import logging
logger = logging.getLogger(__name__)


class OAuth2Client:
    """Cliente OAuth2 para autenticación de usuarios"""
    
    def __init__(self):
        """Inicializa el cliente OAuth2 con las credenciales del entorno"""
        # Priority: OAUTH2_URL (internal k8s) > PUBLIC_OAUTH2_URL (tailscale public)
        # This allows the service to work both in Kubernetes and locally
        self.base_url = os.environ.get("OAUTH2_URL") or os.environ.get("PUBLIC_OAUTH2_URL", "http://localhost:8080").rstrip('/')
        self.client_id = os.environ.get("OAUTH2_CLIENT_ID", "cine-platform")
        self.client_secret = os.environ.get("OAUTH2_CLIENT_SECRET", "cine-platform-secret")
        
        # Log the URL being used
        logger.info(f"[OAuth2Client] Initialized with base_url: {self.base_url}")
        logger.info(f"[OAuth2Client] OAUTH2_URL env: {os.environ.get('OAUTH2_URL', 'NOT SET')}")
        logger.info(f"[OAuth2Client] PUBLIC_OAUTH2_URL env: {os.environ.get('PUBLIC_OAUTH2_URL', 'NOT SET')}")
        
        # Endpoints - Note: OAUTH2_TOKEN_ENDPOINT in configmap uses /oauth/token
        self.token_endpoint = os.environ.get("OAUTH2_TOKEN_ENDPOINT", "/oauth2/token")
        self.authorize_endpoint = os.environ.get("OAUTH2_AUTHORIZE_ENDPOINT", "/oauth2/authorize")
        self.userinfo_endpoint = os.environ.get("OAUTH2_USERINFO_ENDPOINT", "/userinfo")
        self.revoke_endpoint = os.environ.get("OAUTH2_REVOKE_ENDPOINT", "/oauth2/revoke")
        
        logger.info(f"[OAuth2Client] Token endpoint: {self.token_endpoint}")
        logger.info(f"[OAuth2Client] Authorize endpoint: {self.authorize_endpoint}")
        
        # Redirect URI - IMPORTANTE: Debe ser la URL PÚBLICA que el navegador usará
        # ya que el servidor OAuth2 valida que coincida con su redirect_uri registrado
        self.redirect_uri = os.environ.get("PUBLIC_REDIRECT_URI", "http://localhost:5000/oauth/callback").rstrip('/')
        
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
        # Try primary URL first, then fallback
        primary_url = os.environ.get("OAUTH2_URL")
        fallback_url = os.environ.get("PUBLIC_OAUTH2_URL")
        
        urls_to_try = []
        if primary_url:
            urls_to_try.append(primary_url.rstrip('/'))
        if fallback_url and fallback_url != primary_url:
            urls_to_try.append(fallback_url.rstrip('/'))
        
        if not urls_to_try:
            urls_to_try = ["http://localhost:8080"]
        
        last_error = None
        for base_url in urls_to_try:
            url = f"{base_url}{self.token_endpoint}"
            
            # Log detallado para debugging
            logger.info(f"[OAUTH_TOKEN_EXCHANGE] Intentando URL: {url}")
            logger.info(f"[OAUTH_TOKEN_EXCHANGE] Client ID: {self.client_id}")
            logger.info(f"[OAUTH_TOKEN_EXCHANGE] Redirect URI: {self.redirect_uri}")
            
            # Headers que se envían
            auth_header = self._get_basic_auth_header()
            # No loguear el secret completo por seguridad
            auth_header_preview = f"Basic {auth_header['Authorization'].split(' ')[1][:20]}..."
            logger.info(f"[OAUTH_TOKEN_EXCHANGE] Authorization header: {auth_header_preview}")
            
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            }
            
            logger.info(f"[OAUTH_TOKEN_EXCHANGE] Payload: grant_type={payload['grant_type']}, code={code[:20]}..., redirect_uri={self.redirect_uri}, code_verifier={code_verifier[:20]}...")
            
            try:
                logger.info(f"[OAUTH_TOKEN_EXCHANGE] Haciendo petición POST a {url}...")
                response = requests.post(
                    url, 
                    data=payload, 
                    headers=auth_header,
                    timeout=10,
                    verify=False  # Para certificados autofirmados en desarrollo
                )
                
                logger.info(f"[OAUTH_TOKEN_EXCHANGE] Respuesta recibida: status_code={response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    logger.info(f"[OAUTH_TOKEN_EXCHANGE] Token obtenido exitosamente con URL: {url}")
                    return True, data
                else:
                    logger.error(f"[OAUTH_TOKEN_EXCHANGE] Error response from {url}: {response.text}")
                    # Try next URL if available
                    if len(urls_to_try) > 1:
                        logger.warning(f"[OAUTH_TOKEN_EXCHANGE] Error con URL {url}, intentando siguiente...")
                        last_error = {"error": response.text, "status": response.status_code, "url": url}
                        continue
                    return False, {"error": response.text, "status": response.status_code}
                    
            except requests.exceptions.ConnectionError as e:
                logger.error(f"[OAUTH_TOKEN_EXCHANGE] ConnectionError con URL {url}: {e}")
                # Try next URL if available
                if len(urls_to_try) > 1:
                    logger.warning(f"[OAUTH_TOKEN_EXCHANGE] Error de conexión con {url}, intentando siguiente...")
                    last_error = {"error": "Servidor OAuth no disponible", "details": str(e), "url": url}
                    continue
                return False, {"error": "Servidor OAuth no disponible", "details": str(e)}
            except requests.exceptions.Timeout as e:
                logger.error(f"[OAUTH_TOKEN_EXCHANGE] Timeout con URL {url}: {e}")
                return False, {"error": "Timeout conectando al servidor OAuth", "details": str(e)}
            except Exception as e:
                logger.error(f"[OAUTH_TOKEN_EXCHANGE] Error general con URL {url}: {e}")
                return False, {"error": str(e)}
        
        # All URLs failed
        logger.error(f"[OAUTH_TOKEN_EXCHANGE] Todas las URLs fallaron. Última URL intentada: {urls_to_try[-1] if urls_to_try else 'N/A'}")
        return False, last_error or {"error": "Servidor OAuth no disponible en ninguna URL"}
    
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
