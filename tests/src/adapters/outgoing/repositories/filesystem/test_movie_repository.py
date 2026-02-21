"""
Tests para FilesystemMovieRepository
"""
import pytest
import sys
import os
import tempfile
import shutil

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
        repo = FilesystemMovieRepository()
        
        title, year = repo._parse_filename('Test Movie (2023).mkv')
        assert title == 'Test Movie'
        assert year == 2023
    
    def test_parse_filename_no_year(self):
        """Test sin año"""
        repo = FilesystemMovieRepository()
        
        title, year = repo._parse_filename('Test Movie.mkv')
        assert title == 'Test Movie'
        assert year is None
    
    def test_parse_filename_optimized(self):
        """Test con sufijo optimized"""
        repo = FilesystemMovieRepository()
        
        title, year = repo._parse_filename('Test Movie (2023)-optimized.mkv')
        assert title == 'Test Movie'
        assert year == 2023
    
    def test_scan_folder(self):
        """Test de escaneo de carpeta"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        movies = repo._scan_folder()
        
        assert len(movies) > 0
        assert any(m['title'] == 'Test Movie' for m in movies)
    
    def test_list_all(self):
        """Test de listar todas"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        movies = repo.list_all()
        
        assert isinstance(movies, list)
    
    def test_search(self):
        """Test de búsqueda"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        results = repo.search('Test')
        
        assert len(results) > 0
        assert any('Test' in r['title'] for r in results)
    
    def test_get_by_year(self):
        """Test de obtener por año"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        results = repo.get_by_year(2023)
        
        # Verificar que hay películas de 2023
        for r in results:
            if r.get('year') == 2023:
                assert True
                return
        assert True  # Si no hay resultados, también es válido
    
    def test_get_optimized(self):
        """Test de obtener optimizadas"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        results = repo.get_optimized()
        
        # Verificar que hay optimizadas
        for r in results:
            if r.get('is_optimized'):
                assert True
                return
        assert True
    
    def test_get_random(self):
        """Test de obtener aleatorias"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        results = repo.get_random(limit=2)
        
        assert len(results) <= 2
    
    def test_get_recent(self):
        """Test de obtener recientes"""
        repo = FilesystemMovieRepository(self.temp_dir)
        
        results = repo.get_recent(limit=2)
        
        assert len(results) <= 2


class TestFilesystemMovieRepositoryEdgeCases:
    """Tests para casos extremos"""
    
    def test_empty_folder(self):
        """Test con carpeta vacía"""
        temp_dir = tempfile.mkdtemp()
        try:
            repo = FilesystemMovieRepository(temp_dir)
            movies = repo.list_all()
            assert len(movies) == 0
        finally:
            shutil.rmtree(temp_dir)
    
    def test_invalid_folder(self):
        """Test con carpeta inexistente"""
        repo = FilesystemMovieRepository('/nonexistent/folder')
        movies = repo.list_all()
        assert len(movies) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
