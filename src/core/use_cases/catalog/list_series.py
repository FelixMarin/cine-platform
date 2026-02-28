"""
Caso de uso - Listar series del catálogo
"""
from typing import List, Dict, Optional
from src.core.ports.repositories.serie_repository import ISerieRepository


class ListSeriesUseCase:
    """Caso de uso para listar series"""
    
    def __init__(self, serie_repository: ISerieRepository):
        self._repository = serie_repository
    
    def execute(
        self,
        genre: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        Lista series con filtros opcionales
        
        Args:
            genre: Filtrar por género
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de series
        """
        if genre:
            series = self._repository.get_by_genre(genre)
        else:
            series = self._repository.list_all()
        
        # Aplicar paginación
        if offset > 0:
            series = series[offset:]
        
        if limit:
            series = series[:limit]
        
        return series
    
    def get_with_episodes(self, serie_id: int) -> Optional[Dict]:
        """Obtiene una serie con todos sus episodios"""
        return self._repository.get_with_episodes(serie_id)
    
    def get_episodes_by_season(self, serie_id: int, season: int) -> List[Dict]:
        """Obtiene los episodios de una temporada específica"""
        serie = self._repository.get_with_episodes(serie_id)
        if not serie:
            return []
        
        episodes = serie.get('episodes', [])
        return [ep for ep in episodes if ep.get('season') == season]
