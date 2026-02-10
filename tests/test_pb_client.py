import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Añadir el directorio padre al path para importar los módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pb_client import PocketBaseClient


class TestPocketBaseClient(unittest.TestCase):

    def setUp(self):
        self.client = PocketBaseClient("http://test-url")

    @patch('requests.post')
    def test_login_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "fake-token",
            "record": {"id": "123", "email": "test@test.com"}
        }
        mock_post.return_value = mock_response

        success, user_data = self.client.login("test@test.com", "password")

        self.assertTrue(success)
        self.assertEqual(self.client.token, "fake-token")
        self.assertEqual(user_data["email"], "test@test.com")

        mock_post.assert_called_with(
            "http://test-url/api/collections/users/auth-with-password",
            json={"identity": "test@test.com", "password": "password"}
        )

    @patch('requests.post')
    def test_login_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid credentials"}
        mock_post.return_value = mock_response

        success, error = self.client.login("test@test.com", "wrong")

        self.assertFalse(success)
        self.assertEqual(error, "Invalid credentials")

    @patch('requests.post')
    def test_login_exception(self, mock_post):
        mock_post.side_effect = Exception("Connection error")

        success, error = self.client.login("test@test.com", "pass")

        self.assertFalse(success)
        self.assertIn("Connection error", error)

    def test_get_headers(self):
        self.assertEqual(self.client.get_headers(), {})

        self.client.token = "abc"
        self.assertEqual(self.client.get_headers(), {"Authorization": "Bearer abc"})

    @patch('requests.post')
    def test_create_success(self, mock_post):
        self.client.token = "token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "new"}
        mock_post.return_value = mock_response

        success, data = self.client.create("posts", {"title": "Test"})

        self.assertTrue(success)

        mock_post.assert_called_with(
            "http://test-url/api/collections/posts/records",
            json={"title": "Test"},
            headers={"Authorization": "Bearer token"}
        )

    @patch('requests.get')
    def test_list_records(self, mock_get):
        self.client.token = "token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"id": 1}, {"id": 2}]}
        mock_get.return_value = mock_response

        items = self.client.list_records("posts")

        self.assertEqual(len(items), 2)

        mock_get.assert_called_with(
            "http://test-url/api/collections/posts/records",
            params=None,
            headers={"Authorization": "Bearer token"}
        )


if __name__ == '__main__':
    unittest.main()
