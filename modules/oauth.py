import os
from modules.core import IAuthService
from oauth_client import OAuth2Client


class OAuth2AuthAdapter(IAuthService):
    def __init__(self, base_url=None, client_id=None, client_secret=None):

        # Todas las variables son obligatorias
        base_url = base_url or os.environ["OAUTH2_URL"]
        client_id = client_id or os.environ["OAUTH2_CLIENT_ID"]
        client_secret = client_secret or os.environ["OAUTH2_CLIENT_SECRET"]

        self.client = OAuth2Client(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret
        )

    def login(self, email, password):
        return self.client.login(email, password)

    @property
    def token(self):
        return self.client.token
