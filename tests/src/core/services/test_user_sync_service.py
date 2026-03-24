"""
Tests para UserSyncService
"""

import pytest
from unittest.mock import Mock
from src.core.services.UserSyncService import UserSyncService


@pytest.fixture
def mock_repo():
    """Fixture con repositorio mockeado"""
    repo = Mock()
    repo.get_by_oauth_id.return_value = None
    repo.create_from_oauth.return_value = 123
    repo.get_by_id.return_value = {
        "id": 123,
        "oauth_user_id": 456,
        "username": "testuser",
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar_url": None,
        "bio": None,
        "privacy_level": "public",
        "created_at": "2024-01-01",
        "last_active": "2024-01-01",
    }
    return repo


@pytest.fixture
def service(mock_repo):
    """Fixture con servicio inicializado"""
    return UserSyncService(mock_repo)


def test_sync_user_new_user(service, mock_repo):
    """Test sincronización de usuario nuevo"""
    oauth_data = {
        "id": 456,
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["ROLE_USER"],
    }

    result = service.sync_user(oauth_data)

    mock_repo.create_from_oauth.assert_called_once()
    mock_repo.update_last_active.assert_not_called()

    assert result["id"] == 123
    assert result["username"] == "testuser"


def test_sync_user_existing_user(service, mock_repo):
    """Test sincronización de usuario existente"""
    mock_repo.get_by_oauth_id.return_value = {"id": 123}

    oauth_data = {"id": 456, "username": "testuser", "email": "test@example.com"}

    result = service.sync_user(oauth_data)

    mock_repo.update_last_active.assert_called_once_with(123)
    mock_repo.create_from_oauth.assert_not_called()


def test_sync_user_missing_required_field(service):
    """Test error cuando falta campo obligatorio"""
    oauth_data = {"id": 456, "username": "testuser"}

    with pytest.raises(ValueError) as excinfo:
        service.sync_user(oauth_data)

    assert "Campo obligatorio faltante" in str(excinfo.value)


def test_get_user_profile(service, mock_repo):
    """Test obtener perfil por ID"""
    profile = service.get_user_profile(123)

    mock_repo.get_by_id.assert_called_once_with(123)
    assert profile is not None
    assert profile["id"] == 123


def test_get_user_by_oauth_id(service, mock_repo):
    """Test obtener perfil por OAuth ID"""
    mock_repo.get_by_oauth_id.return_value = {"id": 123, "oauth_user_id": 456}

    profile = service.get_user_by_oauth_id(456)

    mock_repo.get_by_oauth_id.assert_called_once_with(456)
    assert profile is not None


def test_update_user_profile(service, mock_repo):
    """Test actualizar perfil"""
    mock_repo.get_by_id.return_value = {"id": 123}
    mock_repo.update_profile.return_value = True

    update_data = {"display_name": "Nuevo Nombre", "bio": "Nueva bio"}

    result = service.update_user_profile(123, update_data)

    assert result is True
    mock_repo.update_profile.assert_called_once_with(123, update_data)


def test_update_user_profile_user_not_found(service, mock_repo):
    """Test actualizar perfil de usuario inexistente"""
    mock_repo.get_by_id.return_value = None

    result = service.update_user_profile(999, {})

    assert result is False
    mock_repo.update_profile.assert_not_called()
