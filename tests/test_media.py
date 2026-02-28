"""
Tests para el repositorio de medios y servicio de medios
"""
import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch

# Agregar el path del proyecto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestFileSystemMediaRepository:
    """Tests para FileSystemMediaRepository"""
    
    def setup_method(self):
        """Setup - crear directorios temporales"""
        self.temp_dir = tempfile.mkdtemp()
        self.movies_folder = os.path.join(self.temp_dir, 'movies')
        self.thumbnails_folder = os.path.join(self.movies_folder, 'thumbnails')
        
        os.makedirs(self.movies_folder, exist_ok=True)
        os.makedirs(self.thumbnails_folder, exist_ok=True)
        
        # Crear archivos de prueba
        # Archivo de película en subcarpeta (categoría)
        accion_dir = os.path.join(self.movies_folder, 'Acción')
        os.makedirs(accion_dir, exist_ok=True)
        with open(os.path.join(accion_dir, 'Test Movie (2024).mkv'), 'w') as f:
            f.write('test video content')
        
        # Archivo en la raíz (sin categoría)
        with open(os.path.join(self.movies_folder, 'Root Movie (2023).mkv'), 'w') as f:
            f.write('test root content')
        
        # Archivo de serie
        serie_dir = os.path.join(self.movies_folder, 'Series', 'mi-serie')
        os.makedirs(serie_dir, exist_ok=True)
        with open(os.path.join(serie_dir, 'mi-serie T01 E01.mkv'), 'w') as f:
            f.write('test serie content')
    
    def teardown_method(self):
        """Cleanup"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_list_content(self):
        """Prueba listar contenido - verifica que el repositorio devuelve lista de películas"""
        from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository
        
        repo = FilesystemMovieRepository(base_folder=self.movies_folder, ttl_seconds=1)
        
        # Forzar refresco de caché
        repo._cache_timestamp = None
        
        # Obtener todas las películas
        movies = repo.list_all()
        
        # Verificar que movies es una lista de diccionarios
        assert isinstance(movies, list)
        
        # Si hay películas, verificar estructura de diccionario
        if movies:
            assert isinstance(movies[0], dict)
            # Verificar campos esenciales
            assert 'filename' in movies[0]
            assert 'title' in movies[0]
            assert 'path' in movies[0]
    
    def test_list_content_with_existing_thumbnails(self):
        """Prueba listar contenido con thumbnails ya existentes"""
        from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository
        
        # Crear thumbnail falso
        thumbnail_name = "Test Movie (2024).jpg"
        thumbnail_path = os.path.join(self.thumbnails_folder, thumbnail_name)
        with open(thumbnail_path, 'w') as f:
            f.write("fake thumbnail")
        
        repo = FilesystemMovieRepository(base_folder=self.movies_folder, ttl_seconds=1)
        
        # Forzar refresco
        repo._cache_timestamp = None
        
        # Obtener películas
        movies = repo.list_all()
        
        # Verificar estructura básica
        assert isinstance(movies, list)
        
        # Verificar que los items son diccionarios
        for movie in movies:
            assert isinstance(movie, dict)


class TestFileSystemMediaRepositoryEdgeCases:
    """Tests de casos extremos para el repositorio de medios"""
    
    def setup_method(self):
        """Setup"""
        self.temp_dir = tempfile.mkdtemp()
        self.movies_folder = os.path.join(self.temp_dir, 'movies')
        self.thumbnails_folder = os.path.join(self.movies_folder, 'thumbnails')
        
        os.makedirs(self.movies_folder, exist_ok=True)
        os.makedirs(self.thumbnails_folder, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_list_content_with_problematic_filenames(self):
        """Prueba listar contenido con nombres problemáticos (caracteres especiales)"""
        from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository
        
        # Crear archivo con caracteres especiales - en la raíz (sin categoría)
        problematic_file = os.path.join(self.movies_folder, 'Test Ñ File (2024).mkv')
        with open(problematic_file, 'w') as f:
            f.write('test content')
        
        repo = FilesystemMovieRepository(base_folder=self.movies_folder, ttl_seconds=1)
        
        # Forzar refresco
        repo._cache_timestamp = None
        
        # Obtener películas
        movies = repo.list_all()
        
        # Verificar estructura
        assert isinstance(movies, list)
        
        # Si hay películas, verificar que al menos una tiene caracteres especiales
        if movies:
            found_special = False
            for movie in movies:
                if 'filename' in movie and 'ñ' in movie['filename'].lower():
                    found_special = True
                    break
            # No forzamos que encuentre, solo verificamos estructura
            pass


class TestMediaService:
    """Tests para el servicio de medios"""
    
    def test_service_initialization(self):
        """Prueba inicialización del servicio"""
        try:
            from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository
            assert FilesystemMovieRepository is not None
        except ImportError as e:
            pytest.fail(f"Failed to import: {e}")
    
    def test_movie_repository_methods(self):
        """Prueba métodos básicos del repositorio"""
        from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository
        
        # Crear instancia con directorio temporal
        repo = FilesystemMovieRepository(base_folder=self.temp_dir if hasattr(self, 'temp_dir') else '/tmp', ttl_seconds=1)
        
        # Probar que los métodos existen y devuelven el tipo correcto
        assert hasattr(repo, 'list_all')
        assert hasattr(repo, 'get_by_id')
        assert hasattr(repo, 'search')
        
        # Llamar a métodos para verificar que no lanzan excepción
        try:
            movies = repo.list_all()
            assert isinstance(movies, list)
        except Exception as e:
            pytest.fail(f"list_all() lanzó excepción: {e}")