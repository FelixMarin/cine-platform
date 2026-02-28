"""
Tests para la entidad User
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.entities.user import User, UserRole, UserPreferences


class TestUserEntity:
    """Tests para la entidad User"""
    
    def test_create_user_basic(self):
        """Test de creación básica"""
        user = User(
            id=1,
            email="test@example.com",
            username="testuser"
        )
        
        assert user.id == 1
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == UserRole.USER
    
    def test_user_default_values(self):
        """Test de valores por defecto"""
        user = User(email="test@example.com")
        
        assert user.id is None
        assert user.username == ""
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.oauth_provider is None
    
    def test_is_admin(self):
        """Test de verificación de admin"""
        user = User(email="admin@example.com", role=UserRole.ADMIN)
        assert user.is_admin is True
        
        user = User(email="user@example.com", role=UserRole.USER)
        assert user.is_admin is False
    
    def test_display_name(self):
        """Test de nombre para mostrar"""
        user = User(email="test@example.com", username="testuser")
        assert user.display_name == "testuser"
        
        user = User(email="test@example.com", username="")
        assert user.display_name == "test"
    
    def test_to_dict(self):
        """Test de conversión a diccionario"""
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            role=UserRole.USER
        )
        
        data = user.to_dict()
        
        assert data['id'] == 1
        assert data['email'] == "test@example.com"
        assert data['role'] == "user"
        assert 'is_admin' in data
        assert 'display_name' in data
    
    def test_from_dict(self):
        """Test de creación desde diccionario"""
        data = {
            'id': 1,
            'email': 'test@example.com',
            'username': 'testuser',
            'role': 'admin'
        }
        
        user = User.from_dict(data)
        
        assert user.id == 1
        assert user.role == UserRole.ADMIN
    
    def test_user_preferences(self):
        """Test de preferencias de usuario"""
        user = User(
            email="test@example.com",
            preferences=UserPreferences(
                default_quality="high_quality",
                autoplay=False,
                subtitles=True,
                language="en"
            )
        )
        
        assert user.preferences.default_quality == "high_quality"
        assert user.preferences.autoplay is False
        assert user.preferences.language == "en"
    
    def test_oauth_user(self):
        """Test de usuario OAuth"""
        user = User(
            email="oauth@example.com",
            username="oauthuser",
            oauth_provider="google",
            oauth_id="google123"
        )
        
        assert user.oauth_provider == "google"
        assert user.oauth_id == "google123"


class TestUserPreferences:
    """Tests para UserPreferences"""
    
    def test_preferences_default(self):
        """Test de valores por defecto"""
        prefs = UserPreferences()
        
        assert prefs.default_quality == "balanced"
        assert prefs.autoplay is True
        assert prefs.subtitles is True
        assert prefs.language == "es"
    
    def test_preferences_to_dict(self):
        """Test de conversión a diccionario"""
        prefs = UserPreferences(default_quality="high_quality", autoplay=False)
        
        data = prefs.to_dict()
        
        assert data['default_quality'] == "high_quality"
        assert data['autoplay'] is False
    
    def test_preferences_from_dict(self):
        """Test de creación desde diccionario"""
        data = {
            'default_quality': 'master',
            'autoplay': True,
            'subtitles': False,
            'language': 'en'
        }
        
        prefs = UserPreferences.from_dict(data)
        
        assert prefs.default_quality == "master"
        assert prefs.autoplay is True
        assert prefs.subtitles is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
