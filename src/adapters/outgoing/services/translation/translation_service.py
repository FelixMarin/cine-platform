"""
Servicio de traducción automática usando deep-translator
Implementa caché en memoria para evitar traducciones repetidas
"""
import os
import logging
import hashlib
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Instancia global del servicio
_translation_service = None


def _get_text_hash(text: str) -> str:
    """Genera un hash curto del texto para logging"""
    return hashlib.md5(text.encode()).hexdigest()[:8]


class TranslationService:
    """Servicio de traducción con caché en memoria"""
    
    def __init__(self, enabled: bool = True, target_lang: str = 'es'):
        """
        Inicializa el servicio de traducción
        
        Args:
            enabled: Si la traducción está habilitada
            target_lang: Idioma destino (por defecto español)
        """
        self._enabled = enabled
        self._target_lang = target_lang
        self._translator = None
        
        if self._enabled:
            try:
                from deep_translator import GoogleTranslator
                self._translator = GoogleTranslator(source='auto', target=self._target_lang)
                logger.info(f"✅ Servicio de traducción inicializado (idioma: {self._target_lang})")
            except Exception as e:
                logger.warning(f"⚠️ Error al inicializar deep-translator: {e}")
                self._enabled = False
    
    @property
    def is_enabled(self) -> bool:
        """Verifica si el servicio está habilitado"""
        return self._enabled and self._translator is not None
    
    def translate(self, text: str, source_title: str = None) -> tuple[str, bool]:
        """
        Traduce un texto al idioma configurado
        
        Args:
            text: Texto a traducir
            source_title: Título de la fuente (para logging)
            
        Returns:
            Tupla con (texto traducido, booleano indicando si fue traducido)
        """
        # Si no está habilitado, devolver texto original
        if not self.is_enabled:
            return text, False
        
        # No traducir si el texto está vacío o es muy corto
        if not text or len(text.strip()) < 10:
            return text, False
        
        try:
            # Verificar si ya está en español (básico)
            text_lower = text.lower()
            if 'español' in text_lower or 'spanish' in text_lower:
                logger.debug(f"📝 Texto ya parece estar en español, retornando original")
                return text, False
            
            # Intentar traducción
            text_hash = _get_text_hash(text)
            
            # Usar el translator con caché
            translated = self._cached_translate(text)
            
            if translated and translated != text:
                if source_title:
                    logger.info(f"🌐 Traduciendo plot de '{source_title}' (hash: {text_hash})")
                return translated, True
            else:
                # Si la traducción falló o devolvió el mismo texto
                return text, False
                
        except Exception as e:
            logger.error(f"❌ Error en traducción: {e}")
            # Graceful degradation: devolver texto original
            return text, False
    
    def _translate_with_cache(self, text: str) -> str:
        """
        Método interno que usa lru_cache para la traducción
        Este método es el que se cachea
        """
        try:
            return self._translator.translate(text)
        except Exception as e:
            logger.warning(f"⚠️ Error en traducción directa: {e}")
            raise
    
    def _cached_translate(self, text: str) -> str:
        """
        Envuelve la traducción con una caché basada en el hash del texto
        """
        # Crear una clave de caché única basada en el texto
        cache_key = (text, self._target_lang)
        
        if cache_key in _translate_cache:
            text_hash = _get_text_hash(text)
            logger.debug(f"✅ Usando traducción cacheada para texto hash: {text_hash}")
            return _translate_cache[cache_key]
        
        # Traducir
        result = self._translator.translate(text)
        
        # Guardar en caché
        if result and result != text:
            _translate_cache[cache_key] = result
            text_hash = _get_text_hash(text)
            logger.debug(f"💾 Guardando en caché traducción (hash: {text_hash})")
        
        return result


# Variable global para la caché (se inicializa con el servicio)
_translate_cache = {}


def _translate_with_cache_cached(text: str, target_lang: str) -> str:
    """
    Traduce con caché en memoria manual (para mayor control)
    """
    cache_key = (text, target_lang)
    
    if cache_key in _translate_cache:
        text_hash = _get_text_hash(text)
        logger.debug(f"✅ Usando traducción cacheada para texto hash: {text_hash}")
        return _translate_cache[cache_key]
    
    # Traducir
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='auto', target=target_lang)
    result = translator.translate(text)
    
    # Guardar en caché
    if result and result != text:
        _translate_cache[cache_key] = result
        text_hash = _get_text_hash(text)
        logger.debug(f"💾 Guardando en caché traducción (hash: {text_hash})")
    
    return result


def get_translation_service() -> TranslationService:
    """
    Obtiene la instancia singleton del servicio de traducción
    """
    global _translation_service
    
    if _translation_service is None:
        enabled = os.environ.get('TRANSLATION_ENABLED', 'true').lower() == 'true'
        target_lang = os.environ.get('TRANSLATION_TARGET_LANG', 'es')
        _translation_service = TranslationService(enabled=enabled, target_lang=target_lang)
    
    return _translation_service


def translate_plot(plot: str, source_title: str = None) -> tuple[str, bool]:
    """
    Función helper para traducir un plot
    
    Args:
        plot: Texto del plot a traducir
        source_title: Título de la película/serie (para logging)
        
    Returns:
        Tupla con (plot traducido, fue_traducido)
    """
    service = get_translation_service()
    return service.translate(plot, source_title)
