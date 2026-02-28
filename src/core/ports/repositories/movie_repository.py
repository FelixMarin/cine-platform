"""
Puerto - Interfaz para repositorio de películas
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict


class IMovieRepository(ABC):
    """Puerto para el repositorio de películas"""
    
    @abstractmethod
    def list_all(self) -> List[Dict]:
        """Lista todas las películas"""
        pass
    
    @abstractmethod
    def get_by_id(self, movie_id: int) -> Optional[Dict]:
        """Obtiene una película por su ID"""
        pass
    
    @abstractmethod
    def get_by_path(self, path: str) -> Optional[Dict]:
        """Obtiene una película por su ruta"""
        pass
    
    @abstractmethod
    def get_by_filename(self, filename: str) -> Optional[Dict]:
        """Obtiene una película por su nombre de archivo"""
        pass
    
    @abstractmethod
    def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Obtiene una película por su ID de IMDb"""
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        """Busca películas por título"""
        pass
    
    @abstractmethod
    def get_by_genre(self, genre: str) -> List[Dict]:
        """Obtiene películas por género"""
        pass
    
    @abstractmethod
    def get_by_year(self, year: int) -> List[Dict]:
        """Obtiene películas por año"""
        pass
    
    @abstractmethod
    def get_optimized(self) -> List[Dict]:
        """Obtiene solo películas optimizadas"""
        pass
    
    @abstractmethod
    def save(self, movie_data: Dict) -> Dict:
        """Guarda o actualiza una película"""
        pass
    
    @abstractmethod
    def delete(self, movie_id: int) -> bool:
        """Elimina una película"""
        pass
    
    @abstractmethod
    def update_metadata(self, movie_id: int, metadata: Dict) -> Dict:
        """Actualiza los metadatos de una película"""
        pass
    
    @abstractmethod
    def get_random(self, limit: int = 10) -> List[Dict]:
        """Obtiene películas aleatorias"""
        pass
    
    @abstractmethod
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Obtiene las películas más recientes"""
        pass
