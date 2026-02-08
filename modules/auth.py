from modules.core import IAuthService
from pb_client import PocketBaseClient

class PocketBaseAuthAdapter(IAuthService):
    def __init__(self, base_url):
        self.client = PocketBaseClient(base_url=base_url)

    def login(self, email, password):
        return self.client.login(email, password)
    
    @property
    def token(self):
        return self.client.token