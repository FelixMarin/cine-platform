"""
Puerto - Interfaz para repositorio de episodios
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict


class IEpisodeRepository(ABC):
    """Puerto para el repositorio de episodios"""
    
    @abstractmethod
    def list_all(self) -> List[Dict]:
        """Lista todos los episodios"""
        pass
    
    @abstractmethod
    def get_by_id(self, episode_id: int) -> Optional[Dict]:
        """Obtiene un episodio por su ID"""
        pass
    
    @abstractmethod
    def get_by_serie_and_number(self, serie_id: int, season: int, episode_number: int) -> Optional[Dict]:
        """Obtiene un episodio por serie, temporada y número"""
        pass
    
    @abstractmethod
    def get_by_serie(self, serie_id: int) -> List[Dict]:
        """Obtiene todos los episodios de una serie"""
        pass
    
    @abstractmethod
    def get_by_season(self, serie_id: int, season: int) -> List[Dict]:
        """Obtiene los episodios de una temporada específica"""
        pass
    
    @abstractmethod
    def save(self, episode_data: Dict) -> Dict:
        """Guarda o actualiza un episodio"""
        pass
    
    @abstractmethod
    def delete(self, episode_id: int) -> bool:
        """Elimina un episodio"""
        pass
    
    @abstractmethod
    def delete_by_serie(self, serie_id: int) -> bool:
        """Elimina todos los episodios de una serie"""
        pass
