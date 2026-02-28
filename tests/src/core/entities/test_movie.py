"""
Tests para la entidad Movie
"""
import pytest
import sys
import os

# Añadir el path del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.entities.movie import Movie


class TestMovieEntity:
    """Tests para la entidad Movie"""
    
    def test_create_movie_basic(self):
        """Test de creación básica de Movie"""
        movie = Movie(
            id=1,
            title="Test Movie",
            year=2023,
            path="/path/to/movie.mkv"
        )
        
        assert movie.id == 1
        assert movie.title == "Test Movie"
        assert movie.year == 2023
        assert movie.path == "/path/to/movie.mkv"
    
    def test_movie_default_values(self):
        """Test de valores por defecto"""
        movie = Movie(title="Test")
        
        assert movie.id is None
        assert movie.year is None
        assert movie.thumbnail is None
        assert movie.is_optimized is False
        assert movie.metadata_source == "local"
    
    def test_title_clean(self):
        """Test de título limpio"""
        # Con año
        movie = Movie(title="Test Movie (2023)")
        assert movie.title_clean == "Test Movie"
        
        # Con sufijo optimized
        movie = Movie(title="Test Movie-optimized")
        assert movie.title_clean == "Test Movie"
        
        # Con año y optimized
        movie = Movie(title="Test Movie (2023)-optimized")
        assert movie.title_clean == "Test Movie"
    
    def test_display_title(self):
        """Test de título para mostrar"""
        movie = Movie(title="Test", year=2023)
        assert movie.display_title == "Test (2023)"
        
        movie = Movie(title="Test", year=None)
        assert movie.display_title == "Test"
    
    def test_size_mb(self):
        """Test de tamaño en MB"""
        movie = Movie(size=1048576)  # 1 MB
        assert movie.size_mb == 1.0
        
        movie = Movie(size=None)
        assert movie.size_mb is None
    
    def test_duration_formatted(self):
        """Test de duración formateada"""
        # 1 hora, 30 minutos, 45 segundos
        movie = Movie(duration=5445)
        assert movie.duration_formatted == "01:30:45"
        
        movie = Movie(duration=None)
        assert movie.duration_formatted is None
    
    def test_to_dict(self):
        """Test de conversión a diccionario"""
        movie = Movie(
            id=1,
            title="Test Movie",
            year=2023,
            path="/path/to/movie.mkv",
            duration=5400
        )
        
        data = movie.to_dict()
        
        assert data['id'] == 1
        assert data['title'] == "Test Movie"
        assert data['year'] == 2023
        assert data['duration'] == 5400
        assert 'title_clean' in data
        assert 'display_title' in data
    
    def test_from_dict(self):
        """Test de creación desde diccionario"""
        data = {
            'id': 1,
            'title': 'Test Movie',
            'year': 2023,
            'path': '/path/to/movie.mkv'
        }
        
        movie = Movie.from_dict(data)
        
        assert movie.id == 1
        assert movie.title == "Test Movie"
        assert movie.year == 2023
    
    def test_movie_optimized_flag(self):
        """Test de flag de optimización"""
        movie = Movie(
            title="Test-optimized",
            is_optimized=True,
            optimized_profile="balanced"
        )
        
        assert movie.is_optimized is True
        assert movie.optimized_profile == "balanced"
    
    def test_movie_imdb_fields(self):
        """Test de campos de IMDB"""
        movie = Movie(
            title="Test",
            imdb_id="tt1234567",
            imdb_rating=8.5,
            genre="Action, Adventure",
            plot="A test plot"
        )
        
        assert movie.imdb_id == "tt1234567"
        assert movie.imdb_rating == 8.5
        assert "Action" in movie.genre
        assert movie.plot == "A test plot"


class TestMovieEdgeCases:
    """Tests para casos extremos de Movie"""
    
    def test_empty_title(self):
        """Test con título vacío"""
        movie = Movie(title="")
        assert movie.title == ""
        assert movie.display_title == ""
    
    def test_special_characters_in_title(self):
        """Test con caracteres especiales"""
        movie = Movie(title="Test: Movie - 2023 (ES)")
        assert "Test" in movie.title_clean
    
    def test_large_file_size(self):
        """Test con tamaño grande de archivo"""
        # 100 GB
        movie = Movie(size=107374182400)
        # 100GB = 102400 MB (no 100000)
        assert movie.size_mb == 102400.0
    
    def test_long_duration(self):
        """Test con duración larga"""
        # 10 horas
        movie = Movie(duration=36000)
        assert movie.duration_formatted == "10:00:00"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
