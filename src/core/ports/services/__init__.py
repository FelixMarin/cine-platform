"""
Puerto - Interfaz para servicios externos de metadatos
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List


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
