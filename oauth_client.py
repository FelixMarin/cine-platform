import os
import base64
import requests
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


class OAuth2Client:
    def __init__(self, base_url=None, client_id=None, client_secret=None):

        # Todas las variables son obligatorias
        self.base_url = (base_url or os.environ["OAUTH2_URL"]).rstrip('/')
        self.client_id = client_id or os.environ["OAUTH2_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["OAUTH2_CLIENT_SECRET"]

        # Endpoints obligatorios (del ConfigMap)
        self.token_endpoint = os.environ["OAUTH2_TOKEN_ENDPOINT"]
        self.userinfo_endpoint = os.environ["OAUTH2_USERINFO_ENDPOINT"]

        self.token = None
        self.user_data = None

    def _basic_auth_header(self):
        raw = f"{self.client_id}:{self.client_secret}".encode()
        encoded = base64.b64encode(raw).decode()
        return {"Authorization": f"Basic {encoded}"}

    def login(self, username, password):
        """Autentica al usuario usando OAuth2 Password Grant."""

        # Construcción dinámica del endpoint
        url = f"{self.base_url}{self.token_endpoint}"
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password
        }

        try:
            response = requests.post(url, data=payload, headers=self._basic_auth_header())
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_data = {"username": username}
                logger.info("Login OK")
                return True, self.user_data
            logger.error(f"Login failed: {response.json()}")
            return False, response.json()
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, str(e)

    def get_headers(self):
        """Devuelve headers con el JWT."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        logger.info("Headers returned OK")
        return headers

    def get(self, url, params=None):
        """GET autenticado."""
        return requests.get(url, params=params, headers=self.get_headers())

    def post(self, url, data=None):
        """POST autenticado."""
        return requests.post(url, json=data, headers=self.get_headers())
