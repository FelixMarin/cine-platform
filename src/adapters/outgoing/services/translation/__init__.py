"""
Servicio de traducción automática
"""
from src.adapters.outgoing.services.translation.translation_service import TranslationService, get_translation_service, translate_plot

__all__ = ['TranslationService', 'get_translation_service', 'translate_plot']
