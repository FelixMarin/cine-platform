"""
Caso de uso - Buscar contenido en el catálogo
"""
from typing import List, Dict, Tuple
from src.core.ports.repositories.movie_repository import IMovieRepository
from src.core.ports.repositories.serie_repository import ISerieRepository


class SearchUseCase:
    """Caso de uso para buscar contenido"""
    
    def __init__(
        self,
        movie_repository: IMovieRepository,
        serie_repository: ISerieRepository
    ):
        self._movie_repository = movie_repository
        self._serie_repository = serie_repository
    
    def execute(self, query: str) -> Dict[str, List[Dict]]:
        """
        Busca películas y series por título
        
        Args:
            query: Término de búsqueda
            
        Returns:
            Diccionario con películas y series encontradas
        """
        movies = self._movie_repository.search(query)
        series = self._serie_repository.search(query)
        
        return {
            'movies': movies,
            'series': series,
            'total': len(movies) + len(series)
        }
    
    def search_movies_only(self, query: str) -> List[Dict]:
        """Busca solo películas"""
        return self._movie_repository.search(query)
    
    def search_series_only(self, query: str) -> List[Dict]:
        """Busca solo series"""
        return self._serie_repository.search(query)
