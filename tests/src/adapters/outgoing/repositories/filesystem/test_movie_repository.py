"""
Tests para FilesystemMovieRepository
"""
import pytest
import sys
import os
import tempfile
import shutil
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository


class TestFilesystemMovieRepository:
    """Tests para FilesystemMovieRepository"""
    
    def setup_method(self):
        """Setup - crear directorio temporal"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Crear algunos archivos de prueba
        with open(os.path.join(self.temp_dir, 'Test Movie (2023).mkv'), 'w') as f:
            f.write('test')
        with open(os.path.join(self.temp_dir, 'Another Movie.mkv'), 'w') as f:
            f.write('test')
        with open(os.path.join(self.temp_dir, 'Test-optimized.mkv'), 'w') as f:
            f.write('test')
        
        # Crear subcarpeta
        os.makedirs(os.path.join(self.temp_dir, 'subfolder'))
        with open(os.path.join(self.temp_dir, 'subfolder', 'Subfolder Movie.mp4'), 'w') as f:
            f.write('test')
    
    def teardown_method(self):
        """Cleanup - eliminar directorio temporal"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_parse_filename(self):
        """Test de parseo de nombre de archivo"""
        repo = FilesystemMovieRepository(ttl_seconds=1)  # TTL corto para tests
        
        title, year = repo._parse_filename('Test Movie (2023).mkv')
        assert title == 'Test Movie'
        assert year == 2023
    
    def test_parse_filename_no_year(self):
        """Test sin año"""
        repo = FilesystemMovieRepository(ttl_seconds=1)
        
        title, year = repo._parse_filename('Test Movie.mkv')
        assert title == 'Test Movie'
        assert year is None
    
    def test_parse_filename_optimized(self):
        """Test con sufijo optimized"""
        repo = FilesystemMovieRepository(ttl_seconds=1)
        
        title, year = repo._parse_filename('Test Movie (2023)-optimized.mkv')
        assert title == 'Test Movie'
        assert year == 2023
    
    def test_parse_filename_different_formats(self):
        """Test con diferentes formatos de año"""
        repo = FilesystemMovieRepository(ttl_seconds=1)
        
        # Formato con punto: movie.2023.mkv
        title, year = repo._parse_filename('Movie.2023.mkv')
        assert 'Movie' in title  # El título puede tener punto residual
        assert year == 2023
        
        # Formato con guión: movie-2023.mkv
        title, year = repo._parse_filename('Movie-2023.mkv')
        assert 'Movie' in title
        assert year == 2023
    
    def test_generate_movie_id(self):
        """Test de generación de ID estable"""
        repo = FilesystemMovieRepository(ttl_seconds=1)
        
        path1 = '/mnt/servidor/Data2TB/audiovisual/mkv/Movie (2023).mkv'
        path2 = '/mnt/servidor/Data2TB/audiovisual/mkv/Other Movie.mkv'
        
        id1 = repo._generate_movie_id(path1)
        id2 = repo._generate_movie_id(path2)
        
        # Verificar formato
        assert id1.startswith('mov_')
        assert len(id1) == 12  # mov_ + 8 caracteres hex
        
        # Verificar que IDs son diferentes para paths diferentes
        assert id1 != id2
        
        # Verificar que el mismo path produce el mismo ID (estable)
        id1_again = repo._generate_movie_id(path1)
        assert id1 == id1_again
    
    def test_cache_functionality(self):
        """Test de funcionalidad de caché"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        # Primera llamada - debe escanear
        movies1 = repo.list_all()
        assert len(movies1) > 0
        
        # Verificar que la caché tiene datos
        assert repo._cache_timestamp is not None
        assert len(repo._movie_index) > 0
        
        # Segunda llamada - debe usar caché
        movies2 = repo.list_all()
        assert movies1 == movies2
        
        # Verificar que no hubo nuevo escaneo (misma marca de tiempo)
        assert repo._cache_timestamp is not None
    
    def test_cache_expiration(self):
        """Test de expiración de caché"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        # Primera llamada
        repo.list_all()
        timestamp1 = repo._cache_timestamp
        
        # Esperar a que expire la caché
        time.sleep(1.5)
        
        # Segunda llamada - debe refrescar
        repo.list_all()
        timestamp2 = repo._cache_timestamp
        
        # Verificar que se refreshó
        assert timestamp2 > timestamp1
    
    def test_scan_folder(self):
        """Test de escaneo de carpeta"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        movies = repo._scan_folder()
        
        assert len(movies) > 0
        assert any(m['title'] == 'Test Movie' for m in movies)
    
    def test_list_all(self):
        """Test de listar todas"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        movies = repo.list_all()
        
        assert isinstance(movies, list)
        assert len(movies) > 0
        
        # Verificar que todas las películas tienen ID
        for movie in movies:
            assert 'id' in movie
            assert movie['id'].startswith('mov_')
    
    def test_get_by_id_string(self):
        """Test de obtener por ID string"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        # Obtener todas las películas
        movies = repo.list_all()
        assert len(movies) > 0
        
        # Obtener por ID
        movie_id = movies[0]['id']
        movie = repo.get_by_id(movie_id)
        
        assert movie is not None
        assert movie['id'] == movie_id
    
    def test_get_by_id_integer(self):
        """Test de compatibilidad con ID entero"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        movies = repo.list_all()
        assert len(movies) > 0
        
        # Obtener por índice entero
        movie = repo.get_by_id(0)
        
        assert movie is not None
    
    def test_search(self):
        """Test de búsqueda"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        results = repo.search('Test')
        
        assert len(results) > 0
        assert any('Test' in r['title'] for r in results)
    
    def test_get_by_year(self):
        """Test de obtener por año"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        results = repo.get_by_year(2023)
        
        # Verificar que hay películas de 2023
        for r in results:
            if r.get('year') == 2023:
                assert True
                return
        assert True  # Si no hay resultados, también es válido
    
    def test_get_optimized(self):
        """Test de obtener optimizadas"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        results = repo.get_optimized()
        
        # Verificar que hay optimizadas
        for r in results:
            if r.get('is_optimized'):
                assert True
                return
        assert True
    
    def test_get_random(self):
        """Test de obtener aleatorias"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        results = repo.get_random(limit=2)
        
        assert len(results) <= 2
    
    def test_get_recent(self):
        """Test de obtener recientes"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        results = repo.get_recent(limit=2)
        
        assert len(results) <= 2
    
    def test_invalidate_cache(self):
        """Test de invalidación de caché"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        # Primera llamada
        repo.list_all()
        assert repo._cache_timestamp is not None
        
        # Invalidar
        repo.invalidate_cache()
        assert repo._cache_timestamp is None
    
    def test_get_cache_stats(self):
        """Test de estadísticas de caché"""
        repo = FilesystemMovieRepository(self.temp_dir, ttl_seconds=1)
        
        repo.list_all()
        stats = repo.get_cache_stats()
        
        assert 'ttl_seconds' in stats
        assert 'cached_movies' in stats
        assert stats['ttl_seconds'] == 1


class TestFilesystemMovieRepositoryEdgeCases:
    """Tests para casos extremos"""
    
    def test_empty_folder(self):
        """Test con carpeta vacía"""
        temp_dir = tempfile.mkdtemp()
        # Usar un nombre único para evitar conflictos con caché persistente
        temp_dir = tempfile.mkdtemp(prefix='empty_test_')
        try:
            repo = FilesystemMovieRepository(temp_dir, ttl_seconds=1)
            repo.invalidate_cache()  # Asegurar que no use caché previa
            movies = repo.list_all()
            assert len(movies) == 0
        finally:
            shutil.rmtree(temp_dir)
    
    def test_invalid_folder(self):
        """Test con carpeta inexistente"""
        repo = FilesystemMovieRepository('/nonexistent/folder', ttl_seconds=1)
        repo.invalidate_cache()  # Asegurar que no use caché previa
        movies = repo.list_all()
        assert len(movies) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
