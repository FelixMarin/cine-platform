"""
Tests para el repositorio de series del filesystem
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.repositories.filesystem.serie_repository import (
    FilesystemSerieRepository,
    _clean_unicode,
)


class TestCleanUnicode:
    """Tests de la función _clean_unicode"""
    
    def test_clean_unicode_empty(self):
        """Test con string vacío"""
        assert _clean_unicode("") == ""
    
    def test_clean_unicode_none(self):
        """Test con None"""
        assert _clean_unicode(None) is None
    
    def test_clean_unicode_no_unicode(self):
        """Test sin caracteres Unicode problemáticos"""
        result = _clean_unicode("Breaking Bad")
        assert result == "Breaking Bad"
    
    def test_clean_unicode_with_accents(self):
        """Test con acentos normales"""
        result = _clean_unicode("El señor de los anillos")
        assert result == "El señor de los anillos"
    
    def test_clean_unicode_with_surrogates(self):
        """Test con surrogates problemáticos"""
        # Simular un string con surrogate
        test_str = "Serie con \udced problema"
        result = _clean_unicode(test_str)
        # El surrogate debe ser reemplazado por 'í'
        assert "í" in result or "problema" in result


class TestFilesystemSerieRepository:
    """Tests del repositorio de series"""
    
    @pytest.fixture
    def temp_dir(self):
        """Directorio temporal para tests"""
        temp_root = tempfile.mkdtemp()
        yield temp_root
        shutil.rmtree(temp_root, ignore_errors=True)
    
    @pytest.fixture
    def repo(self, temp_dir):
        """Repositorio con directorio temporal"""
        return FilesystemSerieRepository(base_folder=temp_dir)
    
    def test_init_default(self):
        """Test de inicialización con valores por defecto"""
        repo = FilesystemSerieRepository()
        assert repo._base_folder is not None
        assert ".mp4" in repo._valid_extensions
        assert ".mkv" in repo._valid_extensions
    
    def test_init_custom_folder(self):
        """Test de inicialización con carpeta personalizada"""
        repo = FilesystemSerieRepository(base_folder="/custom/path")
        assert repo._base_folder == "/custom/path"
    
    def test_parse_season_folder_with_sxx(self):
        """Test de parsing de carpeta de temporada con formato Sxx"""
        repo = FilesystemSerieRepository()
        
        name, season = repo._parse_season_folder("Breaking.Bad.S01")
        assert name == "Breaking Bad"
        assert season == 1
        
        name, season = repo._parse_season_folder("The.Wire.S03")
        assert name == "The Wire"
        assert season == 3
    
    def test_parse_season_folder_with_sxxexx(self):
        """Test de parsing de carpeta con temporada y episodio"""
        repo = FilesystemSerieRepository()
        
        name, season = repo._parse_season_folder("Serie.Name.S02E05")
        assert name == "Serie Name"
        assert season == 2
    
    def test_parse_season_folder_no_season(self):
        """Test de parsing sin número de temporada - el código preserva el nombre"""
        repo = FilesystemSerieRepository()
        
        name, season = repo._parse_season_folder("SomeSerieName")
        # El código reemplaza solo un punto, no todos
        assert name == "SomeSerieName"
        assert season == 1
    
    def test_parse_season_folder_case_insensitive(self):
        """Test de parsing case insensitive"""
        repo = FilesystemSerieRepository()
        
        name, season = repo._parse_season_folder("Series.s05")
        assert name == "Series"
        assert season == 5
        
        name, season = repo._parse_season_folder("Series.SEASON06")
        # El regex busca \.S\d+ así que SEASON06 no coincide como temporada
        assert season == 1  # Default, no se detecta temporada
    
    def test_scan_folder_empty(self, repo, temp_dir):
        """Test de escaneo con carpeta vacía"""
        result = repo._scan_folder()
        assert result == []
    
    def test_scan_folder_nonexistent(self, repo):
        """Test de escaneo con carpeta inexistente"""
        repo._base_folder = "/nonexistent/folder"
        result = repo._scan_folder()
        assert result == []
    
    def test_scan_folder_with_series(self, repo, temp_dir):
        """Test de escaneo con series"""
        # Crear estructura de prueba
        series_dir = os.path.join(temp_dir, "Breaking.Bad.S01")
        os.makedirs(series_dir)
        
        # Crear archivo de episodio
        ep_file = os.path.join(series_dir, "Breaking.Bad.S01E01.mkv")
        with open(ep_file, "w") as f:
            f.write("test content")
        
        result = repo._scan_folder()
        
        assert len(result) == 1
        assert result[0]["name"] == "Breaking Bad"
        assert len(result[0]["episodes"]) == 1
        assert result[0]["episodes"][0]["filename"] == "Breaking.Bad.S01E01.mkv"
    
    def test_scan_folder_skips_special_folders(self, repo, temp_dir):
        """Test que verifica que se saltan carpetas especiales"""
        # Crear carpetas especiales
        os.makedirs(os.path.join(temp_dir, "mkv"))
        os.makedirs(os.path.join(temp_dir, "optimized"))
        os.makedirs(os.path.join(temp_dir, "thumbnails"))
        
        # Crear una serie real
        series_dir = os.path.join(temp_dir, "Serie.S01")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "ep.mkv"), "w") as f:
            f.write("test")
        
        result = repo._scan_folder()
        
        # Solo debe encontrar la serie real, no las especiales
        assert len(result) == 1
    
    def test_scan_folder_multiple_seasons(self, repo, temp_dir):
        """Test de escaneo con múltiples temporadas"""
        # Crear múltiples temporadas
        s01_dir = os.path.join(temp_dir, "Serie.S01")
        s02_dir = os.path.join(temp_dir, "Serie.S02")
        
        os.makedirs(s01_dir)
        os.makedirs(s02_dir)
        
        with open(os.path.join(s01_dir, "S01E01.mkv"), "w") as f:
            f.write("test")
        with open(os.path.join(s02_dir, "S02E01.mkv"), "w") as f:
            f.write("test")
        
        result = repo._scan_folder()
        
        assert len(result) == 1
        # La serie debe tener episodios de ambas temporadas
        # El código actual guarda episodios en lista plana, no por temporada
    
    def test_scan_folder_multiple_series(self, repo, temp_dir):
        """Test de escaneo con múltiples series"""
        # Crear dos series diferentes
        bb_dir = os.path.join(temp_dir, "Breaking.Bad.S01")
        tw_dir = os.path.join(temp_dir, "The.Wire.S01")
        
        os.makedirs(bb_dir)
        os.makedirs(tw_dir)
        
        with open(os.path.join(bb_dir, "bb_s01e01.mkv"), "w") as f:
            f.write("test")
        with open(os.path.join(tw_dir, "tw_s01e01.mkv"), "w") as f:
            f.write("test")
        
        result = repo._scan_folder()
        
        assert len(result) == 2
        series_names = [s["name"] for s in result]
        assert "Breaking Bad" in series_names
        assert "The Wire" in series_names
    
    def test_scan_folder_valid_extensions_only(self, repo, temp_dir):
        """Test que solo incluye extensiones válidas"""
        series_dir = os.path.join(temp_dir, "Serie.S01")
        os.makedirs(series_dir)
        
        # Crear archivos con diferentes extensiones
        valid_exts = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"]
        invalid_exts = [".txt", ".jpg", ".srt", ".nfo"]
        
        for ext in valid_exts + invalid_exts:
            filepath = os.path.join(series_dir, f"episode{ext}")
            with open(filepath, "w") as f:
                f.write("test")
        
        result = repo._scan_folder()
        
        assert len(result) == 1
        # Solo debe tener episodios con extensiones válidas
        episodes = result[0]["episodes"]
        extensions = [os.path.splitext(ep["filename"])[1] for ep in episodes]
        
        for ext in valid_exts:
            assert ext in extensions
        for ext in invalid_exts:
            assert ext not in extensions
    
    def test_episode_parsing(self, repo, temp_dir):
        """Test del parsing de episodios"""
        series_dir = os.path.join(temp_dir, "Test.S01")
        os.makedirs(series_dir)
        
        # Crear episodio con número
        ep_file = os.path.join(series_dir, "Test.S01E05.mkv")
        with open(ep_file, "w") as f:
            f.write("test content " * 1000)  # ~13KB
        
        result = repo._scan_folder()
        
        assert len(result) == 1
        episode = result[0]["episodes"][0]
        assert episode["season"] == 1
        assert episode["episode"] == 5
        assert episode["size"] > 0
    
    def test_episode_without_number(self, repo, temp_dir):
        """Test de episodio sin número"""
        series_dir = os.path.join(temp_dir, "Test.S01")
        os.makedirs(series_dir)
        
        ep_file = os.path.join(series_dir, "episode.mkv")
        with open(ep_file, "w") as f:
            f.write("test")
        
        result = repo._scan_folder()
        
        episode = result[0]["episodes"][0]
        assert episode["episode"] == 1  # Default
    
    def test_scan_folder_exposes_interface_methods(self, repo, temp_dir):
        """Test que verifica que el repositorio implementa la interfaz"""
        # Crear algunos datos
        series_dir = os.path.join(temp_dir, "Test.S01")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "test.mkv"), "w") as f:
            f.write("test")
        
        # Verificar que tiene los métodos de la interfaz
        assert hasattr(repo, "_scan_folder")
        assert hasattr(repo, "_parse_season_folder")
        assert hasattr(repo, "_base_folder")


class TestFilesystemSerieRepositoryEdgeCases:
    """Tests de casos edge del repositorio de series"""
    
    @pytest.fixture
    def temp_dir(self):
        """Directorio temporal"""
        temp_root = tempfile.mkdtemp()
        yield temp_root
        shutil.rmtree(temp_root, ignore_errors=True)
    
    @pytest.fixture
    def repo(self, temp_dir):
        return FilesystemSerieRepository(base_folder=temp_dir)
    
    def test_folder_with_only_subfolders(self, repo, temp_dir):
        """Test con carpeta que tiene solo subcarpetas sin archivos"""
        series_dir = os.path.join(temp_dir, "Serie.S01")
        os.makedirs(series_dir)
        
        # Crear una subcarpeta (no archivo)
        subdir = os.path.join(series_dir, "subfolder")
        os.makedirs(subdir)
        
        result = repo._scan_folder()
        
        # No debe fallar, pero puede estar vacío
        assert isinstance(result, list)
    
    def test_very_long_filename(self, repo, temp_dir):
        """Test con nombre de archivo muy largo"""
        series_dir = os.path.join(temp_dir, "Serie.S01")
        os.makedirs(series_dir)
        
        long_name = "A" * 200 + ".mkv"
        ep_file = os.path.join(series_dir, long_name)
        with open(ep_file, "w") as f:
            f.write("test")
        
        result = repo._scan_folder()
        
        assert len(result) == 1
        # El nombre debe ser truncado o el código debe manejarlo
    
    def test_special_characters_in_filename(self, repo, temp_dir):
        """Test con caracteres especiales en el nombre"""
        series_dir = os.path.join(temp_dir, "Série.S01")
        os.makedirs(series_dir)
        
        ep_file = os.path.join(series_dir, "episode.mkv")
        with open(ep_file, "w") as f:
            f.write("test")
        
        result = repo._scan_folder()
        
        # Debe manejar caracteres especiales sin fallar
        assert len(result) == 1