import pytest
from src.adapters.outgoing.repositories.cine.app_user_repository import (
    AppUserRepository,
)


@pytest.fixture
def repo():
    return AppUserRepository()


def test_repository_initialization(repo):
    """Verificar que el repositorio se inicializa correctamente"""
    assert repo is not None
    assert repo.engine is not None
