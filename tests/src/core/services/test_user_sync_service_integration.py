"""
Tests de integración para UserSyncService (requiere BD real)
"""

import pytest
from src.adapters.outgoing.repositories.cine.app_user_repository import (
    AppUserRepository,
)
from src.core.services.UserSyncService import UserSyncService


@pytest.mark.skip(reason="Requiere tablas en BD")
class TestUserSyncServiceIntegration:
    def setup_method(self):
        """Configurar repositorio y servicio para cada test"""
        self.repo = AppUserRepository()
        self.service = UserSyncService(self.repo)

        self.test_oauth_data = {
            "id": 9999,
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["ROLE_USER"],
            "display_name": "Test User",
        }

    def test_sync_new_user(self):
        """Test sincronizar usuario nuevo"""
        result = self.service.sync_user(self.test_oauth_data)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["display_name"] == "Test User"

        user_from_db = self.repo.get_by_oauth_id(9999)
        assert user_from_db is not None
        assert user_from_db["id"] == result["id"]

    def test_sync_existing_user(self):
        """Test sincronizar usuario existente"""
        first_result = self.service.sync_user(self.test_oauth_data)

        second_result = self.service.sync_user(self.test_oauth_data)

        assert second_result["id"] == first_result["id"]

        assert second_result["last_active"] != first_result["last_active"]

    def test_update_profile_through_service(self):
        """Test actualizar perfil vía servicio"""
        user = self.service.sync_user(self.test_oauth_data)

        update_data = {"display_name": "Updated Name", "bio": "New bio"}
        success = self.service.update_user_profile(user["id"], update_data)
        assert success is True

        updated = self.service.get_user_profile(user["id"])
        assert updated["display_name"] == "Updated Name"
        assert updated["bio"] == "New bio"

    def test_get_user_by_oauth_id(self):
        """Test obtener por OAuth ID"""
        user = self.service.sync_user(self.test_oauth_data)

        found = self.service.get_user_by_oauth_id(9999)
        assert found is not None
        assert found["id"] == user["id"]
