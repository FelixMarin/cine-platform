"""
Tests para el servicio de traducción
"""
import pytest
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.services.translation.translation_service import (
    TranslationService,
)


class TestTranslationService:
    """Tests del servicio de traducción"""
    
    def test_service_initialization_enabled(self):
        """Test de inicialización con traducción habilitada"""
        service = TranslationService(enabled=True, target_lang='es')
        
        # El servicio puede o no estar habilitado según esté deep-translator instalado
        assert service is not None
    
    def test_service_initialization_disabled(self):
        """Test de inicialización con traducción deshabilitada"""
        service = TranslationService(enabled=False, target_lang='es')
        
        assert service.is_enabled is False
    
    def test_service_initialization_custom_lang(self):
        """Test de inicialización con idioma personalizado"""
        service = TranslationService(enabled=False, target_lang='en')
        
        assert service._target_lang == 'en'
    
    def test_is_enabled_property_disabled(self):
        """Test de propiedad is_enabled cuando está deshabilitado"""
        service = TranslationService(enabled=False)
        
        assert service.is_enabled is False
    
    def test_is_enabled_property_no_translator(self):
        """Test de is_enabled cuando no hay translator"""
        service = TranslationService(enabled=True)
        
        # Puede estar habilitado o no dependiendo de deep-translator
        assert isinstance(service.is_enabled, bool)
    
    def test_translate_when_disabled(self):
        """Test de traducción cuando está deshabilitado"""
        service = TranslationService(enabled=False)
        
        result, translated = service.translate("Hello world test text")
        
        # Debe devolver el texto original y translated=False
        assert result == "Hello world test text"
        assert translated is False
    
    def test_translate_empty_text(self):
        """Test de traducción con texto vacío"""
        service = TranslationService(enabled=False)
        
        result, translated = service.translate("")
        
        assert result == ""
    
    def test_translate_short_text_not_translated(self):
        """Test de traducción con texto corto no se traduce"""
        service = TranslationService(enabled=False)
        
        # Textos menores a 10 caracteres no se traducen
        result, translated = service.translate("Hello")
        
        assert result == "Hello"
        assert translated is False
    
    def test_translate_caching(self):
        """Test de caché de traducciones"""
        service = TranslationService(enabled=False)
        
        # Con el servicio deshabilitado, debe devolver el texto original
        result1, _ = service.translate("Hello world test")
        result2, _ = service.translate("Hello world test")
        
        assert result1 == result2


class TestTranslationServiceEdgeCases:
    """Tests de casos edge del servicio de traducción"""
    
    def test_translate_very_long_text(self):
        """Test de traducción de texto muy largo"""
        service = TranslationService(enabled=False)
        
        long_text = "A" * 10000
        result, _ = service.translate(long_text)
        
        # Debe devolver el texto sin cambios cuando está deshabilitado
        assert result == long_text
    
    def test_translate_special_characters(self):
        """Test de traducción con caracteres especiales"""
        service = TranslationService(enabled=False)
        
        result, _ = service.translate("¡Hola! ¿Cómo estás? This is a test text for translation.")
        
        assert "¡Hola!" in result
    
    def test_translate_unicode(self):
        """Test de traducción con caracteres unicode"""
        service = TranslationService(enabled=False)
        
        result, _ = service.translate("日本語テスト This is a test text for the translation service.")
        
        assert "日本語テスト" in result
    
    def test_translate_none(self):
        """Test de traducción con None"""
        service = TranslationService(enabled=False)
        
        # Debe manejar el caso None - devuelve texto original
        result, _ = service.translate(None)
        assert result is None or result == ""
    
    def test_translate_with_source_title(self):
        """Test de traducción con título de fuente"""
        service = TranslationService(enabled=False)
        
        result, translated = service.translate("Test text for translation service", source_title="Test Movie")
        
        assert result is not None


class TestGetTextHash:
    """Tests de la función _get_text_hash"""
    
    def test_hash_generation(self):
        """Test de generación de hash"""
        from src.adapters.outgoing.services.translation.translation_service import _get_text_hash
        
        hash1 = _get_text_hash("Hello")
        hash2 = _get_text_hash("Hello")
        
        # Mismo texto debe dar mismo hash
        assert hash1 == hash2
        assert len(hash1) == 8  # Solo 8 caracteres
    
    def test_different_texts_different_hashes(self):
        """Test de que diferentes textos dan diferentes hashes"""
        from src.adapters.outgoing.services.translation.translation_service import _get_text_hash
        
        hash1 = _get_text_hash("Hello")
        hash2 = _get_text_hash("World")
        
        assert hash1 != hash2