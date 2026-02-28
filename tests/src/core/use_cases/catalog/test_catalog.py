"""
Tests para casos de uso de Catálogo
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.use_cases.catalog import ListMoviesUseCase, ListSeriesUseCase, SearchUseCase


# Mock repository
class MockMovieRepository:
    def __init__(self, movies=None):
        self._movies = movies or []
    
    def list_all(self):
        return self._movies
    
    def get_by_genre(self, genre):
        return [m for m in self._movies if m.get('genre') == genre]
    
    def get_by_year(self, year):
        return [m for m in self._movies if m.get('year') == year]
    
    def get_optimized(self):
        return [m for m in self._movies if m.get('is_optimized')]
    
    def get_random(self, limit=10):
        return self._movies[:limit]
    
    def get_recent(self, limit=20):
        return self._movies[:limit]
    
    def search(self, query):
        return [m for m in self._movies if query.lower() in m.get('title', '').lower()]


class MockSerieRepository:
    def __init__(self, series=None):
        self._series = series or []
    
    def list_all(self):
        return self._series
    
    def get_by_genre(self, genre):
        return [s for s in self._series if s.get('genre') == genre]
    
    def search(self, query):
        return [s for s in self._series if query.lower() in s.get('name', '').lower()]


class TestListMoviesUseCase:
    """Tests para ListMoviesUseCase"""
    
    def test_list_all_movies(self):
        """Test de listar todas las películas"""
        movies = [
            {'id': 1, 'title': 'Movie 1'},
            {'id': 2, 'title': 'Movie 2'}
        ]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.execute()
        
        assert len(result) == 2
    
    def test_filter_by_genre(self):
        """Test de filtro por género"""
        movies = [
            {'id': 1, 'title': 'Movie 1', 'genre': 'Action'},
            {'id': 2, 'title': 'Movie 2', 'genre': 'Drama'}
        ]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.execute(genre='Action')
        
        assert len(result) == 1
        assert result[0]['genre'] == 'Action'
    
    def test_filter_by_year(self):
        """Test de filtro por año"""
        movies = [
            {'id': 1, 'title': 'Movie 1', 'year': 2023},
            {'id': 2, 'title': 'Movie 2', 'year': 2022}
        ]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.execute(year=2023)
        
        assert len(result) == 1
        assert result[0]['year'] == 2023
    
    def test_optimized_only(self):
        """Test de solo optimizadas"""
        movies = [
            {'id': 1, 'title': 'Movie 1', 'is_optimized': True},
            {'id': 2, 'title': 'Movie 2', 'is_optimized': False}
        ]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.execute(optimized_only=True)
        
        assert len(result) == 1
        assert result[0]['is_optimized'] is True
    
    def test_pagination(self):
        """Test de paginación"""
        movies = [{'id': i, 'title': f'Movie {i}'} for i in range(20)]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.execute(limit=5, offset=10)
        
        assert len(result) == 5
        assert result[0]['id'] == 10
    
    def test_get_random(self):
        """Test de películas aleatorias"""
        movies = [{'id': i, 'title': f'Movie {i}'} for i in range(10)]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.get_random(limit=5)
        
        assert len(result) == 5
    
    def test_get_recent(self):
        """Test de películas recientes"""
        movies = [{'id': i, 'title': f'Movie {i}'} for i in range(10)]
        repo = MockMovieRepository(movies)
        use_case = ListMoviesUseCase(repo)
        
        result = use_case.get_recent(limit=5)
        
        assert len(result) == 5


class TestSearchUseCase:
    """Tests para SearchUseCase"""
    
    def test_search_movies_and_series(self):
        """Test de búsqueda en películas y series"""
        movies = [{'id': 1, 'title': 'Test Movie'}]
        series = [{'id': 1, 'name': 'Test Serie'}]
        
        movie_repo = MockMovieRepository(movies)
        serie_repo = MockSerieRepository(series)
        use_case = SearchUseCase(movie_repo, serie_repo)
        
        result = use_case.execute('test')
        
        assert result['total'] == 2
        assert len(result['movies']) == 1
        assert len(result['series']) == 1
    
    def test_search_movies_only(self):
        """Test de búsqueda solo en películas"""
        movies = [{'id': 1, 'title': 'Test Movie'}]
        serie_repo = MockSerieRepository([])
        
        use_case = SearchUseCase(MockMovieRepository(movies), serie_repo)
        
        result = use_case.search_movies_only('test')
        
        assert len(result) == 1


class TestListSeriesUseCase:
    """Tests para ListSeriesUseCase"""
    
    def test_list_all_series(self):
        """Test de listar todas las series"""
        series = [
            {'id': 1, 'name': 'Serie 1'},
            {'id': 2, 'name': 'Serie 2'}
        ]
        repo = MockSerieRepository(series)
        use_case = ListSeriesUseCase(repo)
        
        result = use_case.execute()
        
        assert len(result) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
