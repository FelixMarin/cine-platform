"""
Tests de integración para AppUserRepository (requiere BD real)
"""

import pytest
from src.adapters.outgoing.repositories.cine.app_user_repository import (
    AppUserRepository,
)


@pytest.mark.skip(reason="Requiere tablas en BD")
class TestAppUserRepositoryIntegration:
    def setup_method(self):
        """Configurar repositorio para cada test"""
        self.repo = AppUserRepository()
        self.test_oauth_data = {
            "id": 9999,
            "username": "testuser",
            "email": "test@example.com",
            "display_name": "Test User",
        }

    def test_create_and_get_user(self):
        """Test crear usuario y recuperarlo"""
        user_id = self.repo.create_from_oauth(self.test_oauth_data)
        assert user_id is not None

        user = self.repo.get_by_id(user_id)
        assert user is not None
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"

        user_by_oauth = self.repo.get_by_oauth_id(9999)
        assert user_by_oauth is not None
        assert user_by_oauth["id"] == user_id

    def test_update_profile(self):
        """Test actualizar perfil"""
        user_id = self.repo.create_from_oauth(self.test_oauth_data)

        update_data = {
            "display_name": "Nuevo Nombre",
            "bio": "Esta es mi bio",
            "privacy_level": "followers",
        }
        result = self.repo.update_profile(user_id, update_data)
        assert result is True

        user = self.repo.get_by_id(user_id)
        assert user["display_name"] == "Nuevo Nombre"
        assert user["bio"] == "Esta es mi bio"
        assert user["privacy_level"] == "followers"

    def test_update_last_active(self):
        """Test actualizar última actividad"""
        user_id = self.repo.create_from_oauth(self.test_oauth_data)

        user_before = self.repo.get_by_id(user_id)
        last_active_before = user_before["last_active"]

        self.repo.update_last_active(user_id)

        user_after = self.repo.get_by_id(user_id)
        assert user_after["last_active"] != last_active_before

    def test_user_exists(self):
        """Test verificar existencia"""
        user_id = self.repo.create_from_oauth(self.test_oauth_data)

        exists = self.repo.user_exists(9999)
        assert exists is True

        not_exists = self.repo.user_exists(8888)
        assert not_exists is False
