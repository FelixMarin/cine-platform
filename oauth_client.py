import base64
import requests

class OAuth2Client:
    def __init__(self, base_url="http://oauth2-server:8080", client_id="cine-platform", client_secret="supersecreto"):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.user_data = None

    def _basic_auth_header(self):
        raw = f"{self.client_id}:{self.client_secret}".encode()
        encoded = base64.b64encode(raw).decode()
        return {"Authorization": f"Basic {encoded}"}

    def login(self, username, password):
        """Autentica al usuario usando OAuth2 Password Grant."""
        url = f"{self.base_url}/oauth/token"
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
                # El usuario real está dentro del JWT, no en la respuesta
                self.user_data = {"username": username}
                return True, self.user_data
            return False, response.json()
        except Exception as e:
            return False, str(e)

    def get_headers(self):
        """Devuelve headers con el JWT."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get(self, url, params=None):
        """GET autenticado."""
        return requests.get(url, params=params, headers=self.get_headers())

    def post(self, url, data=None):
        """POST autenticado."""
        return requests.post(url, json=data, headers=self.get_headers())
