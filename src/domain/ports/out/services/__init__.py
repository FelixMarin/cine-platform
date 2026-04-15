"""
Puertos - Servicios del dominio (interfaces)
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.ports.out.services.auth_service import IAuthService
from src.domain.ports.out.services.encoder_service import IEncoderService
from src.domain.ports.out.services.queue_service import IQueueService
from src.domain.ports.out.services.IFileFinder import IFileFinder
from src.domain.ports.out.services.ICleanupService import ICleanupService
from src.domain.ports.out.services.INameSanitizer import INameSanitizer
from src.domain.ports.out.services.IOptimizerAPI import IOptimizerAPI
from src.domain.ports.out.services.IOptimizationHistoryService import IOptimizationHistoryService
from src.domain.ports.out.services.ITokenDecoder import ITokenDecoder


class IMetadataService(ABC):
    """Puerto para servicios de metadatos (OMDB, TMDB, etc.)"""

    @abstractmethod
    def get_movie_metadata(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Obtiene metadatos de una película"""
        pass

    @abstractmethod
    def get_serie_metadata(self, serie_name: str) -> Optional[Dict]:
        """Obtiene metadatos de una serie"""
        pass

    @abstractmethod
    def search_movies(self, query: str) -> List[Dict]:
        """Busca películas por título"""
        pass

    @abstractmethod
    def get_poster_url(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """Obtiene la URL del póster de una película"""
        pass

    @abstractmethod
    def get_serie_poster_url(self, serie_name: str) -> Optional[str]:
        """Obtiene la URL del póster de una serie"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el servicio está disponible"""
        pass


__all__ = [
    'IAuthService',
    'IEncoderService',
    'IQueueService',
    'IFileFinder',
    'ICleanupService',
    'INameSanitizer',
    'IOptimizerAPI',
    'IOptimizationHistoryService',
    'IMetadataService',
    'ITokenDecoder',
]
