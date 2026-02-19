"""
Tests unitarios para el módulo media
Ejecutar con: pytest tests/test_media.py -v
"""

import os
import sys
import tempfile
import shutil
import pytest
import time
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.media import FileSystemMediaRepository, sanitize_for_log

class TestFileSystemMediaRepository:
    """Tests para el repositorio de medios"""
    
    def setup_method(self):
        """Configuración inicial para cada test"""
        # Reset Singleton para evitar estado compartido entre tests
        FileSystemMediaRepository._instance = None

        self.temp_dir = tempfile.mkdtemp()
        self.movies_folder = os.path.join(self.temp_dir, "movies")
        os.makedirs(self.movies_folder)
        
        # Crear estructura de prueba
        self.action_folder = os.path.join(self.movies_folder, "Acción")
        os.makedirs(self.action_folder)
        
        # Crear archivos de prueba
        self.test_video = os.path.join(self.action_folder, "test_movie.mkv")
        with open(self.test_video, 'wb') as f:
            f.write(b'0' * 1024 * 1024)  # 1MB
        
        self.serie_folder = os.path.join(self.movies_folder, "Series")
        os.makedirs(self.serie_folder)
        self.serie_file = os.path.join(self.serie_folder, "mi-serie T01 E01.mkv")
        with open(self.serie_file, 'wb') as f:
            f.write(b'0' * 512 * 1024)  # 512KB
        
        self.thumbnails_folder = os.path.join(self.movies_folder, "thumbnails")
        os.makedirs(self.thumbnails_folder)
        
        # Inicializar repositorio
        self.repo = FileSystemMediaRepository(self.movies_folder)
        
        # Esperar a que el procesador de thumbnails se inicie
        time.sleep(0.5)
    
    def teardown_method(self):
        """Limpiar después de cada test"""
        # Detener procesador
        self.repo.processing_active = False
        if self.repo.processing_thread and self.repo.processing_thread.is_alive():
            self.repo.processing_thread.join(timeout=1)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # ===== TESTS DE SEGURIDAD =====
    
    def test_get_movies_folder(self):
        """Prueba que get_movies_folder devuelve la carpeta correcta"""
        assert self.repo.get_movies_folder() == self.movies_folder
    
    def test_is_path_safe_valid(self):
        """Prueba is_path_safe con rutas válidas"""
        # Ruta dentro de movies_folder
        valid_path = os.path.join(self.movies_folder, "Acción", "test_movie.mkv")
        assert self.repo.is_path_safe(valid_path) == True
        
        # La propia carpeta
        assert self.repo.is_path_safe(self.movies_folder) == True
    
    def test_is_path_safe_invalid(self):
        """Prueba is_path_safe con rutas no válidas"""
        # Ruta fuera de movies_folder
        invalid_path = "/etc/passwd"
        assert self.repo.is_path_safe(invalid_path) == False
        
        # Path traversal
        traversal_path = os.path.join(self.movies_folder, "..", "..", "etc", "passwd")
        assert self.repo.is_path_safe(traversal_path) == False
        
        # Ruta vacía
        assert self.repo.is_path_safe("") == False
        assert self.repo.is_path_safe(None) == False
    
    def test_get_safe_path_valid(self):
        """Prueba get_safe_path con rutas válidas"""
        safe_path = self.repo.get_safe_path("Acción/test_movie.mkv")
        assert safe_path == os.path.join(self.movies_folder, "Acción", "test_movie.mkv")
    
    def test_get_safe_path_invalid(self):
        """Prueba get_safe_path con path traversal"""
        # Intentar salir del directorio base
        invalid = "../../../etc/passwd"
        assert self.repo.get_safe_path(invalid) is None
    
    # ===== TESTS DE FUNCIONALIDAD =====
    
    def test_singleton(self):
        """Prueba que la clase es singleton"""
        repo2 = FileSystemMediaRepository(self.movies_folder)
        assert repo2 is self.repo
    
    def test_get_thumbnails_folder(self):
        """Prueba que devuelve la carpeta correcta de thumbnails"""
        assert self.repo.get_thumbnails_folder() == self.thumbnails_folder
    
    def test_list_content(self):
        """Prueba listar contenido"""
        categorias, series = self.repo.list_content()
        
        # Verificar categorías
        assert "Acción" in categorias
        assert len(categorias["Acción"]) == 1
        assert categorias["Acción"][0]["name"] == "Test Movie"
        
        # Verificar series
        assert len(series) == 1
        serie_name = list(series.keys())[0]
        assert "Mi Serie" in serie_name
        assert len(series[serie_name]) == 1
    
    def test_list_content_with_existing_thumbnails(self):
        """Prueba listar contenido con thumbnails ya existentes"""
        # Crear thumbnail falso
        thumbnail_name = "test_movie.jpg"
        thumbnail_path = os.path.join(self.thumbnails_folder, thumbnail_name)
        with open(thumbnail_path, 'w') as f:
            f.write("fake thumbnail")
        
        categorias, _ = self.repo.list_content()
        
        # Verificar que detecta el thumbnail existente
        assert categorias["Acción"][0]["thumbnail_pending"] == False
        assert categorias["Acción"][0]["thumbnail"] == f"/thumbnails/{thumbnail_name}"
    
    @patch('modules.media.FileSystemMediaRepository._get_video_duration')
    @patch('modules.media.subprocess.run')
    def test_generate_thumbnail_success(self, mock_run, mock_get_duration):
        """Prueba generación exitosa de thumbnail"""
        # Configurar mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        mock_get_duration.return_value = 120.0
        
        # Llamar al método privado directamente
        thumbnail_path = os.path.join(self.thumbnails_folder, "test.jpg")
        result = self.repo._generate_thumbnail(self.test_video, thumbnail_path)
        
        assert result == True
        mock_run.assert_called_once()
        
        # Verificar que se usó lista de argumentos (seguro)
        args, kwargs = mock_run.call_args
        assert isinstance(args[0], list)  # Debe ser lista
        assert "ffmpeg" in args[0]
        assert "-i" in args[0]
        assert self.test_video in args[0]
    
    @patch('modules.media.subprocess.run')
    def test_generate_thumbnail_failure(self, mock_run):
        """Prueba error en generación de thumbnail"""
        mock_run.side_effect = Exception("Error simulado")
        
        thumbnail_path = os.path.join(self.thumbnails_folder, "test.jpg")
        result = self.repo._generate_thumbnail(self.test_video, thumbnail_path)
        
        assert result == False

    @patch('modules.media.magic.from_file', return_value='video/mp4')
    @patch('modules.media.subprocess.run')
    def test_get_video_duration_success(self, mock_run, mock_magic):
        """Prueba obtener duración del video"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "123.45\n"
        mock_run.return_value = mock_result
        
        duration = self.repo._get_video_duration(self.test_video)
        
        assert duration == 123.45
        mock_run.assert_called_once()
        
        # Verificar uso seguro
        args, kwargs = mock_run.call_args
        assert isinstance(args[0], list)
        assert "ffprobe" in args[0]
    
    @patch('modules.media.subprocess.run')
    def test_get_video_duration_failure(self, mock_run):
        """Prueba error al obtener duración"""
        mock_run.side_effect = Exception("Error")
        
        duration = self.repo._get_video_duration(self.test_video)
        assert duration is None
    
    def test_queue_thumbnail_generation(self):
        """Prueba encolar generación de thumbnail"""
        base_name = "test_movie"
        result = self.repo._queue_thumbnail_generation(self.test_video, base_name)
        
        assert result == True
        assert base_name in self.repo.queued_thumbnails
        assert self.repo.thumbnail_queue.qsize() == 1
        
        # Segunda vez no debe encolar
        result2 = self.repo._queue_thumbnail_generation(self.test_video, base_name)
        assert result2 == False
    
    def test_get_thumbnail_status(self):
        """Prueba obtener estado de thumbnails"""
        status = self.repo.get_thumbnail_status()
        
        assert "queue_size" in status
        assert "total_pending" in status
        assert "processed" in status
        assert "processing" in status
        assert status["processing"] == True
    
    def test_clean_filename(self):
        """Prueba limpieza de nombres de archivo"""
        # Nombre normal
        clean = self.repo._clean_filename("test_movie.mkv")
        assert clean == "Test Movie"
        
        # Con sufijos
        clean = self.repo._clean_filename("mi-video-optimized.mp4")
        assert clean == "Mi Video"
        
        clean = self.repo._clean_filename("serie-name_optimized.mkv")
        assert clean == "Serie Name"
        
        # Con números
        clean = self.repo._clean_filename("video 123 parte 2.mp4")
        assert "123" in clean
    
    def test_sanitize_for_log(self):
        """Prueba sanitización para logs"""
        # Texto normal
        assert sanitize_for_log("test") == "test"
        
        # None
        assert sanitize_for_log(None) == ""
        
        # Caracteres especiales
        assert sanitize_for_log("test\uD800test") == "test?test"
        
        # Bytes
        assert sanitize_for_log(b"test") == "b'test'"
    
    @patch('modules.media.subprocess.run')
    def test_check_ffmpeg_webp_support(self, mock_run):
        """Prueba verificación de soporte WebP"""
        mock_result = MagicMock()
        mock_result.stdout = "libwebp"
        mock_run.return_value = mock_result
        
        assert self.repo._check_ffmpeg_webp_support() == True
        
        mock_result.stdout = "no webp"
        assert self.repo._check_ffmpeg_webp_support() == False
    
    @patch('modules.media.subprocess.run')
    def test_generate_thumbnail_webp(self, mock_run):
        """Prueba generación de thumbnail WebP"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        webp_path = os.path.join(self.thumbnails_folder, "test.webp")
        result = self.repo._generate_thumbnail(self.test_video, webp_path)
        
        assert result == True
        args, kwargs = mock_run.call_args
        assert "-c:v" in args[0]
        assert "libwebp" in args[0]


class TestFileSystemMediaRepositoryEdgeCases:
    """Tests de casos extremos"""
    
    def setup_method(self):
        # Reset Singleton para evitar estado compartido entre tests
        FileSystemMediaRepository._instance = None

        self.temp_dir = tempfile.mkdtemp()
        self.movies_folder = os.path.join(self.temp_dir, "movies")
        os.makedirs(self.movies_folder)
        
        # Crear algunos archivos con nombres problemáticos
        self.problematic_file = os.path.join(self.movies_folder, "test_ñ_file.mp4")
        with open(self.problematic_file, 'wb') as f:
            f.write(b'test')
        
        self.repo = FileSystemMediaRepository(self.movies_folder)
    
    def teardown_method(self):
        self.repo.processing_active = False
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_list_content_with_problematic_filenames(self):
        """Prueba listar contenido con nombres problemáticos"""
        categorias, series = self.repo.list_content()
        assert "Sin categoría" in categorias
        assert len(categorias["Sin categoría"]) >= 1
    
    def test_is_path_safe_with_unicode(self):
        """Prueba is_path_safe con caracteres unicode"""
        valid_path = os.path.join(self.movies_folder, "test\u00F1o.mp4")
        assert self.repo.is_path_safe(valid_path) == True
    
    def test_get_safe_path_with_unicode(self):
        """Prueba get_safe_path con caracteres unicode"""
        filename = "test\u00F1o.mp4"
        safe_path = self.repo.get_safe_path(filename)
        expected = os.path.join(self.movies_folder, filename)
        assert safe_path == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])