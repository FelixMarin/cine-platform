from modules.core import IAuthService
from oauth_client import OAuth2Client

class OAuth2AuthAdapter(IAuthService):
    def __init__(self, base_url, client_id="cine-platform", client_secret="supersecreto"):
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
