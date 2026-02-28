import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Asegurar que el módulo se puede importar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.adapters.outgoing.services.oauth.client import OAuth2Client


class TestOAuth2Client(unittest.TestCase):

    def setUp(self):
        # Mockear todas las variables de entorno obligatorias
        self.env = {
            "OAUTH2_URL": "http://auth-server",
            "OAUTH2_CLIENT_ID": "client123",
            "OAUTH2_CLIENT_SECRET": "secret123",
            "OAUTH2_TOKEN_ENDPOINT": "/oauth/token",
            "OAUTH2_AUTHORIZE_ENDPOINT": "/oauth2/authorize",
            "OAUTH2_USERINFO_ENDPOINT": "/user/me",
            "OAUTH2_REDIRECT_URI": "http://localhost:5000/oauth/callback"
        }

    @patch.dict(os.environ, {}, clear=True)
    def test_init_uses_env_vars(self):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            self.assertEqual(client.base_url, "http://auth-server")
            self.assertEqual(client.client_id, "client123")
            self.assertEqual(client.client_secret, "secret123")
            self.assertEqual(client.token_endpoint, "/oauth/token")
            self.assertEqual(client.authorize_endpoint, "/oauth2/authorize")
            self.assertEqual(client.userinfo_endpoint, "/user/me")

    @patch.dict(os.environ, {}, clear=True)
    def test_basic_auth_header(self):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            headers = client._get_basic_auth_header()
            self.assertIn("Authorization", headers)
            self.assertTrue(headers["Authorization"].startswith("Basic "))

    @patch.dict(os.environ, {}, clear=True)
    def test_generate_code_verifier(self):
        """Test de generación de code_verifier"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            verifier = client.generate_code_verifier()
            
            # El verifier debe tener entre 43 y 128 caracteres
            self.assertGreaterEqual(len(verifier), 43)
            self.assertLessEqual(len(verifier), 128)
            # No debe contener caracteres = de padding
            self.assertNotIn('=', verifier)

    @patch.dict(os.environ, {}, clear=True)
    def test_generate_code_challenge(self):
        """Test de generación de code_challenge desde verifier"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            verifier = "test_verifier_12345"
            challenge = client.generate_code_challenge(verifier)
            
            # El challenge debe ser una cadena codificada en base64url
            self.assertIsInstance(challenge, str)
            self.assertGreater(len(challenge), 0)
            # No debe contener caracteres = de padding
            self.assertNotIn('=', challenge)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_authorization_url(self):
        """Test de generación de URL de autorización con PKCE"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            
            code_verifier = "test_verifier_12345"
            state = "random_state_123"
            
            url = client.get_authorization_url(code_verifier, state)
            
            # Verificar que la URL contiene los parámetros correctos
            self.assertIn("/oauth2/authorize", url)
            self.assertIn("response_type=code", url)
            self.assertIn("client_id=client123", url)
            self.assertIn("redirect_uri=", url)
            self.assertIn("scope=openid+profile+read+write", url)
            self.assertIn("code_challenge=", url)
            self.assertIn("code_challenge_method=S256", url)
            self.assertIn("state=random_state_123", url)

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_exchange_code_for_token_success(self, mock_post):
        """Test de intercambio de código por token"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "abc123",
                "refresh_token": "refresh_abc123",
                "token_type": "Bearer"
            }
            mock_post.return_value = mock_response

            ok, data = client.exchange_code_for_token("auth_code", "code_verifier")

            self.assertTrue(ok)
            self.assertEqual(client.token, "abc123")
            self.assertEqual(client.refresh_token, "refresh_abc123")

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_exchange_code_for_token_failure(self, mock_post):
        """Test de fallo en intercambio de código"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()

            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "invalid_grant"
            mock_post.return_value = mock_response

            ok, error = client.exchange_code_for_token("invalid_code", "code_verifier")

            self.assertFalse(ok)
            self.assertIn("error", error)

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_refresh_access_token(self, mock_post):
        """Test de refresco de token"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_token_xyz",
                "refresh_token": "new_refresh_xyz"
            }
            mock_post.return_value = mock_response

            ok, data = client.refresh_access_token("old_refresh_token")

            self.assertTrue(ok)
            self.assertEqual(client.token, "new_token_xyz")

    @patch("requests.get")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_userinfo(self, mock_get):
        """Test de obtener información del usuario"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            client.token = "test_token"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "sub": "123",
                "email": "test@example.com",
                "name": "Test User"
            }
            mock_get.return_value = mock_response

            user_info = client.get_userinfo()

            self.assertIsNotNone(user_info)
            self.assertEqual(user_info["email"], "test@example.com")

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_revoke_token(self, mock_post):
        """Test de revocación de token"""
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            client.token = "test_token"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = client.revoke_token()

            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
