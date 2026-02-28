"""
Caso de uso - Listar películas del catálogo
"""
from typing import List, Dict, Optional
from src.core.ports.repositories.movie_repository import IMovieRepository


class ListMoviesUseCase:
    """Caso de uso para listar películas"""
    
    def __init__(self, movie_repository: IMovieRepository):
        self._repository = movie_repository
    
    def execute(
        self,
        genre: Optional[str] = None,
        year: Optional[int] = None,
        optimized_only: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        Lista películas con filtros opcionales
        
        Args:
            genre: Filtrar por género
            year: Filtrar por año
            optimized_only: Solo mostrar optimizadas
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de películas
        """
        if genre:
            movies = self._repository.get_by_genre(genre)
        elif year:
            movies = self._repository.get_by_year(year)
        elif optimized_only:
            movies = self._repository.get_optimized()
        else:
            movies = self._repository.list_all()
        
        # Aplicar paginación
        if offset > 0:
            movies = movies[offset:]
        
        if limit:
            movies = movies[:limit]
        
        return movies
    
    def get_random(self, limit: int = 10) -> List[Dict]:
        """Obtiene películas aleatorias"""
        return self._repository.get_random(limit)
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Obtiene las películas más recientes"""
        return self._repository.get_recent(limit)
