import requests

class PocketBaseClient:
    def __init__(self, base_url="http://127.0.0.1:8070"):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.user_data = None

    def login(self, email, password):
        """Autentica a un usuario y guarda su token."""
        url = f"{self.base_url}/api/collections/users/auth-with-password"
        payload = {"identity": email, "password": password}
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.user_data = data.get("record")
                return True, self.user_data
            return False, response.json().get("message", "Error desconocido")
        except Exception as e:
            return False, str(e)

    def get_headers(self):
        """Genera headers con el JWT si existe."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def create(self, collection, data):
        """Crea un registro en cualquier colección."""
        url = f"{self.base_url}/api/collections/{collection}/records"
        response = requests.post(url, json=data, headers=self.get_headers())
        return response.status_code in [200, 204], response.json()

    def list_records(self, collection, params=None):
        """Lista registros de una colección (permite filtros, sorts, etc)."""
        url = f"{self.base_url}/api/collections/{collection}/records"
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json().get("items", []) if response.status_code == 200 else []