"""
Puerto - Interfaz para repositorio de series
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict


class ISerieRepository(ABC):
    """Puerto para el repositorio de series"""
    
    @abstractmethod
    def list_all(self) -> List[Dict]:
        """Lista todas las series"""
        pass
    
    @abstractmethod
    def get_by_id(self, serie_id: int) -> Optional[Dict]:
        """Obtiene una serie por su ID"""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Dict]:
        """Obtiene una serie por su nombre"""
        pass
    
    @abstractmethod
    def get_by_path(self, path: str) -> Optional[Dict]:
        """Obtiene una serie por su ruta"""
        pass
    
    @abstractmethod
    def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Obtiene una serie por su ID de IMDb"""
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        """Busca series por nombre"""
        pass
    
    @abstractmethod
    def get_by_genre(self, genre: str) -> List[Dict]:
        """Obtiene series por género"""
        pass
    
    @abstractmethod
    def save(self, serie_data: Dict) -> Dict:
        """Guarda o actualiza una serie"""
        pass
    
    @abstractmethod
    def delete(self, serie_id: int) -> bool:
        """Elimina una serie"""
        pass
    
    @abstractmethod
    def update_metadata(self, serie_id: int, metadata: Dict) -> Dict:
        """Actualiza los metadatos de una serie"""
        pass
    
    @abstractmethod
    def get_with_episodes(self, serie_id: int) -> Optional[Dict]:
        """Obtiene una serie con todos sus episodios"""
        pass
