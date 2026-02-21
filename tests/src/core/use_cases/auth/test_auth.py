"""
Tests para casos de uso de Auth
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.use_cases.auth.login import LoginUseCase, LogoutUseCase


class MockAuthService:
    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.token = "mock_token_12345"
        self.user_data = {
            'id': 1,
            'email': 'test@example.com',
            'name': 'Test User'
        }
    
    def login(self, email, password):
        if self.should_succeed:
            return (True, {'token': self.token, 'user': self.user_data})
        return (False, {'error': 'Invalid credentials'})
    
    def logout(self, user_id):
        return True
    
    def verify_token(self, token):
        return True
    
    def get_user_from_token(self, token):
        return self.user_data


class MockUserRepository:
    def __init__(self):
        self.users = {}
    
    def get_by_oauth(self, provider, oauth_id):
        return None
    
    def update_last_login(self, user_id):
        return True
    
    def save(self, user_data):
        user_data['id'] = 1
        self.users[1] = user_data
        return user_data


class TestLoginUseCase:
    """Tests para LoginUseCase"""
    
    def test_execute_success(self):
        """Test de login exitoso"""
        auth_service = MockAuthService(should_succeed=True)
        
        use_case = LoginUseCase(auth_service)
        success, result = use_case.execute('test@example.com', 'password123')
        
        assert success is True
        assert 'token' in result
        assert 'user' in result
    
    def test_execute_failure(self):
        """Test de login fallido"""
        auth_service = MockAuthService(should_succeed=False)
        
        use_case = LoginUseCase(auth_service)
        success, result = use_case.execute('test@example.com', 'wrongpassword')
        
        assert success is False
        assert 'error' in result
    
    def test_execute_with_user_repository(self):
        """Test con user repository"""
        auth_service = MockAuthService(should_succeed=True)
        user_repo = MockUserRepository()
        
        use_case = LoginUseCase(auth_service, user_repo)
        success, result = use_case.execute('test@example.com', 'password123')
        
        assert success is True
    
    def test_verify_token(self):
        """Test de verificación de token"""
        auth_service = MockAuthService()
        
        use_case = LoginUseCase(auth_service)
        result = use_case.verify_token('test_token')
        
        assert result is True
    
    def test_get_user_from_token(self):
        """Test de obtener usuario desde token"""
        auth_service = MockAuthService()
        
        use_case = LoginUseCase(auth_service)
        result = use_case.get_user_from_token('test_token')
        
        assert result is not None
        assert result['email'] == 'test@example.com'
    
    def test_oauth_login_existing(self):
        """Test de OAuth login con usuario existente"""
        auth_service = MockAuthService()
        user_repo = MockUserRepository()
        
        # Add existing user
        user_repo.users[1] = {'id': 1, 'email': 'test@example.com'}
        
        use_case = LoginUseCase(auth_service, user_repo)
        success, result = use_case.oauth_login('google', 'oauth123', 'test@example.com', 'testuser')
        
        assert success is True
    
    def test_oauth_login_new(self):
        """Test de OAuth login con nuevo usuario"""
        auth_service = MockAuthService()
        user_repo = MockUserRepository()
        
        use_case = LoginUseCase(auth_service, user_repo)
        success, result = use_case.oauth_login('google', 'oauth123', 'new@example.com', 'newuser')
        
        assert success is True
        assert result is not None
    
    def test_oauth_login_no_repo(self):
        """Test de OAuth sin repositorio"""
        auth_service = MockAuthService()
        
        use_case = LoginUseCase(auth_service, None)
        success, result = use_case.oauth_login('google', 'oauth123', 'test@example.com', 'testuser')
        
        assert success is False


class TestLogoutUseCase:
    """Tests para LogoutUseCase"""
    
    def test_execute(self):
        """Test de logout"""
        auth_service = MockAuthService()
        
        use_case = LogoutUseCase(auth_service)
        result = use_case.execute(1)
        
        assert result is True
    
    def test_execute_no_user(self):
        """Test sin usuario"""
        auth_service = MockAuthService()
        
        use_case = LogoutUseCase(auth_service)
        result = use_case.execute(None)
        
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
