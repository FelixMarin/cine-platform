import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Asegurar que el módulo se puede importar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oauth_client import OAuth2Client


class TestOAuth2Client(unittest.TestCase):

    def setUp(self):
        # Mockear todas las variables de entorno obligatorias
        self.env = {
            "OAUTH2_URL": "http://auth-server",
            "OAUTH2_CLIENT_ID": "client123",
            "OAUTH2_CLIENT_SECRET": "secret123",
            "OAUTH2_TOKEN_ENDPOINT": "/oauth/token",
            "OAUTH2_USERINFO_ENDPOINT": "/userinfo"
        }

    @patch.dict(os.environ, {}, clear=True)
    def test_init_uses_env_vars(self):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            self.assertEqual(client.base_url, "http://auth-server")
            self.assertEqual(client.client_id, "client123")
            self.assertEqual(client.client_secret, "secret123")
            self.assertEqual(client.token_endpoint, "/oauth/token")

    @patch.dict(os.environ, {}, clear=True)
    def test_basic_auth_header(self):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            headers = client._basic_auth_header()
            self.assertIn("Authorization", headers)
            self.assertTrue(headers["Authorization"].startswith("Basic "))

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_login_success(self, mock_post):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"access_token": "abc123"}
            mock_post.return_value = mock_response

            ok, data = client.login("user", "pass")

            self.assertTrue(ok)
            self.assertEqual(client.token, "abc123")
            self.assertEqual(data["username"], "user")

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_login_failure(self, mock_post):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()

            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_post.return_value = mock_response

            ok, error = client.login("user", "wrong")

            self.assertFalse(ok)
            self.assertEqual(error["error"], "invalid_grant")

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_login_exception(self, mock_post):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()

            mock_post.side_effect = Exception("Network down")

            ok, error = client.login("user", "pass")

            self.assertFalse(ok)
            self.assertIn("Network down", error)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_headers(self):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            self.assertEqual(client.get_headers(), {})

            client.token = "xyz"
            self.assertEqual(client.get_headers(), {"Authorization": "Bearer xyz"})

    @patch("requests.get")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_authenticated(self, mock_get):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            client.token = "abc"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            client.get("http://test")

            mock_get.assert_called_with(
                "http://test",
                params=None,
                headers={"Authorization": "Bearer abc"}
            )

    @patch("requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_post_authenticated(self, mock_post):
        with patch.dict(os.environ, self.env):
            client = OAuth2Client()
            client.token = "abc"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            client.post("http://test", {"a": 1})

            mock_post.assert_called_with(
                "http://test",
                json={"a": 1},
                headers={"Authorization": "Bearer abc"}
            )


if __name__ == "__main__":
    unittest.main()
