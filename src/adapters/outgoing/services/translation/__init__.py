"""
Servicio de traducción automática
"""
from src.adapters.outgoing.services.translation.async_translation_service import (
    get_plot_es_from_database,
    translate_plot_async,
    translate_plot_background_only,
)
from src.adapters.outgoing.services.translation.translation_service import (
    TranslationService,
    get_translation_service,
    translate_plot,
)

__all__ = ['TranslationService', 'get_translation_service', 'translate_plot', 'translate_plot_async', 'translate_plot_background_only', 'get_plot_es_from_database']
