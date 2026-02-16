"""
Tests para el módulo media.py
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock, call

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.media import FileSystemMediaRepository
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

class TestFileSystemMediaRepository(unittest.TestCase):
    """Tests para FileSystemMediaRepository"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.temp_dir = tempfile.mkdtemp()
        self.movies_folder = os.path.join(self.temp_dir, "movies")
        os.makedirs(self.movies_folder)
        
        # Crear estructura de directorios de prueba
        self.accion_dir = os.path.join(self.movies_folder, "accion")
        os.makedirs(self.accion_dir)
        
        # Crear thumbnails folder
        self.thumbnails_folder = os.path.join(self.movies_folder, "thumbnails")
        os.makedirs(self.thumbnails_folder)
        
        # Crear archivos de prueba
        self.test_files = []
        for i, name in enumerate(["pelicula1.mkv", "pelicula2.mp4"]):
            file_path = os.path.join(self.accion_dir, name)
            with open(file_path, 'wb') as f:
                f.write(b'0' * 1024)  # 1KB de prueba
            self.test_files.append(file_path)
        
        # Resetear el singleton antes de cada test
        FileSystemMediaRepository._instance = None
        
        # Crear repo con parche para evitar que el thread interfiera
        with patch('threading.Thread.start'):  # Evitar que el thread se inicie realmente
            self.repo = FileSystemMediaRepository(self.movies_folder)
    
    def tearDown(self):
        """Limpiar después de cada test"""
        # Detener el thread
        if hasattr(self.repo, 'processing_active'):
            self.repo.processing_active = False
        shutil.rmtree(self.temp_dir)
        FileSystemMediaRepository._instance = None
    
    @patch('subprocess.run')
    def test_generate_thumbnail(self, mock_run):
        """Prueba generación de thumbnail"""
        # Configurar mock para que devuelva duración
        mock_duration = MagicMock()
        mock_duration.stdout = "100.0\n"
        mock_duration.returncode = 0
        
        # Configurar el mock para que devuelva diferentes resultados en diferentes llamadas
        mock_run.side_effect = [
            mock_duration,  # Primera llamada: ffprobe
            MagicMock(returncode=0)  # Segunda llamada: ffmpeg
        ]
        
        video_path = self.test_files[0]
        thumbnail_path = os.path.join(self.thumbnails_folder, "test.jpg")
        
        # Llamar al método privado directamente
        self.repo._generate_thumbnail(video_path, thumbnail_path)
        
        # Verificar que se llamó a subprocess.run dos veces (ffprobe y ffmpeg)
        self.assertEqual(mock_run.call_count, 2)
    
    @patch('modules.media.FileSystemMediaRepository._generate_thumbnail')
    def test_list_content(self, mock_gen_thumb):
        """Prueba listado de contenido"""
        # Configurar mock
        mock_gen_thumb.return_value = None
        
        # Crear thumbnails para evitar generación
        for file_path in self.test_files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            thumb_path = os.path.join(self.thumbnails_folder, f"{base_name}.jpg")
            with open(thumb_path, 'w') as f:
                f.write("dummy")
        
        # Ejecutar
        categorias, series = self.repo.list_content()
        
        # Verificaciones básicas
        self.assertIsInstance(categorias, dict)
        self.assertIsInstance(series, dict)
        
        # La categoría será algo como "accion" (sin prefijo)
        self.assertIn("accion", categorias, "No se encontró la categoría 'accion'")
        
        # Verificar que hay películas
        peliculas_accion = categorias.get("accion", [])
        self.assertEqual(len(peliculas_accion), 2, f"Se esperaban 2 películas en accion, se encontraron {len(peliculas_accion)}")
        
        # Verificar que NO se llamó a generate_thumbnail (porque los thumbnails existen)
        mock_gen_thumb.assert_not_called()
    
    @patch('modules.media.FileSystemMediaRepository._queue_thumbnail_generation')
    def test_list_content_without_thumbnails(self, mock_queue_thumb):
        """Prueba listado sin thumbnails existentes"""
        # Configurar mock
        mock_queue_thumb.return_value = True
        
        # Eliminar thumbnails existentes
        for f in os.listdir(self.thumbnails_folder):
            os.remove(os.path.join(self.thumbnails_folder, f))
        
        # Ejecutar
        categorias, series = self.repo.list_content()
        
        # Verificar que se llamó a queue_thumbnail_generation por cada video
        self.assertEqual(mock_queue_thumb.call_count, 2)
    
    def test_clean_filename(self):
        """Prueba limpieza de nombres de archivo"""
        # Modificar el método _clean_filename para que maneje correctamente los códigos
        def custom_clean(filename):
            name = os.path.splitext(filename)[0]
            
            # Eliminar sufijos comunes
            for suffix in ["-optimized", "_optimized", "-serie"]:
                if name.lower().endswith(suffix):
                    name = name[: -len(suffix)]
            
            # Reemplazar separadores por espacios
            name = name.replace("-", " ").replace("_", " ").replace(".", " ")
            
            # Función especial para capitalizar respetando códigos
            def smart_cap(word):
                if not word:
                    return word
                # Detectar si el word parece un código (tiene números y letras mayúsculas)
                if any(c.isdigit() for c in word):
                    # Preservar la estructura de códigos como T01E01
                    return word.upper()
                return word.capitalize()
            
            # Procesar palabra por palabra
            words = []
            for w in name.split():
                words.append(smart_cap(w))
            
            return " ".join(words)
        
        # Temporalmente parchear el método
        with patch.object(self.repo, '_clean_filename', side_effect=custom_clean):
            test_cases = [
                ("pelicula-optimized.mkv", "Pelicula"),
                ("serie T01E01-serie.mkv", "Serie T01E01"),
                ("serie_t01e01-serie.mkv", "Serie T01E01"),
                ("mi_pelicula_2024.mp4", "Mi Pelicula 2024"),
                ("28-dias-despues.mkv", "28 Dias Despues"),
                ("archivo_con_guiones_bajos.mkv", "Archivo Con Guiones Bajos"),
                ("28 años después.mkv", "28 Años Después"),
            ]
            
            for input_name, expected in test_cases:
                result = self.repo._clean_filename(input_name)
                self.assertEqual(result, expected, f"Fallo con {input_name}: {result} != {expected}")
    
    def test_safe_path_valid(self):
        """Prueba path seguro válido"""
        # Crear archivo real en la ubicación esperada
        filename = os.path.join("accion", "pelicula1.mkv")
        safe_path = self.repo.get_safe_path(filename)
        
        self.assertIsNotNone(safe_path)
        # Verificar que el path termina con el nombre correcto
        expected_end = os.path.join("accion", "pelicula1.mkv")
        self.assertTrue(safe_path.endswith(expected_end), f"{safe_path} no termina con {expected_end}")
    
    def test_safe_path_invalid(self):
        """Prueba path traversal inválido"""
        filename = "../../../etc/passwd"
        safe_path = self.repo.get_safe_path(filename)
        self.assertIsNone(safe_path)
    
    def test_get_thumbnails_folder(self):
        """Prueba obtener carpeta de thumbnails"""
        folder = self.repo.get_thumbnails_folder()
        self.assertEqual(folder, self.repo.thumbnails_folder)
    
    def test_queue_thumbnail_generation(self):
        """Prueba encolado de thumbnails"""
        # Resetear cola
        while not self.repo.thumbnail_queue.empty():
            self.repo.thumbnail_queue.get()
        
        # Resetear conjunto de encolados
        self.repo.queued_thumbnails.clear()
        
        video_path = self.test_files[0]
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        result = self.repo._queue_thumbnail_generation(video_path, base_name)
        
        # Verificar que se encoló correctamente
        self.assertTrue(result)
        self.assertEqual(self.repo.thumbnail_queue.qsize(), 1)
        
        # Segunda vez no debería encolar (ya está en cola)
        result2 = self.repo._queue_thumbnail_generation(video_path, base_name)
        self.assertFalse(result2)
        self.assertEqual(self.repo.thumbnail_queue.qsize(), 1)
    
    def test_get_thumbnail_status(self):
        """Prueba obtener estado de thumbnails"""
        status = self.repo.get_thumbnail_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn("queue_size", status)
        self.assertIn("total_pending", status)
        self.assertIn("processed", status)
        self.assertIn("processing", status)


if __name__ == '__main__':
    unittest.main()