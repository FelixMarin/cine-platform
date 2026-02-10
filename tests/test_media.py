import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Asegurar que el proyecto está en el PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# --- LIMPIEZA DE MÓDULOS MOCKEADOS ---
for mod in list(sys.modules.keys()):
    if mod.startswith("modules.core") or mod.startswith("modules.media"):
        del sys.modules[mod]

from modules.media import FileSystemMediaRepository


class TestFileSystemMediaRepository(unittest.TestCase):

    def setUp(self):
        self.repo = FileSystemMediaRepository("/tmp/movies")


    @patch('modules.media.subprocess.run')
    def test_generate_thumbnail(self, mock_run):
        self.repo._generate_thumbnail("video.mp4", "thumb.jpg")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]

        self.assertIn("ffmpeg", args)
        self.assertIn("video.mp4", args)
        self.assertIn("thumb.jpg", args)


    @patch('modules.media.subprocess.run')
    def test_generate_thumbnail_error(self, mock_run):
        mock_run.side_effect = Exception("FFmpeg failed")

        try:
            self.repo._generate_thumbnail("video.mp4", "thumb.jpg")
        except Exception:
            self.fail("Should handle subprocess error gracefully")


    def test_clean_filename(self):
        name = self.repo._clean_filename("matrix-optimized.mp4")
        self.assertEqual(name, "Matrix")

        name = self.repo._clean_filename("breaking_bad_s01e01-serie.mkv")
        self.assertEqual(name, "Breaking Bad S01e01")

        name = self.repo._clean_filename("my_movie.2023.avi")
        self.assertEqual(name, "My Movie 2023")


    @patch('modules.media.FileSystemMediaRepository._generate_thumbnail')
    @patch('os.path.exists')
    @patch('os.walk')
    def test_list_content(self, mock_walk, mock_exists, mock_gen_thumb):
        # Simular estructura de archivos
        mock_walk.return_value = [
            ("/tmp/movies", [], ["movie1.mp4", "series1 T01E01-serie.mkv", "ignored.txt"]),
        ]

        # Simular existencia de thumbnails
        def exists_side_effect(path):
            if path.endswith("thumbnails"):
                return True
            if "movie1" in path:
                return True  # thumbnail ya existe
            return False      # thumbnail faltante → debe generarse

        mock_exists.side_effect = exists_side_effect

        movies, series = self.repo.list_content()

        # Películas
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0]['name'], "Movie1")

        # Series
        self.assertIn("Series1", series)
        self.assertEqual(len(series["Series1"]), 1)

        # Debe generarse thumbnail para el que no existe
        mock_gen_thumb.assert_called_once()


    def test_get_safe_path(self):
        # Path válido
        path = self.repo.get_safe_path("movie.mp4")
        self.assertTrue(path.startswith(os.path.abspath("/tmp/movies")))

        # Intento de path traversal
        path = self.repo.get_safe_path("../etc/passwd")
        self.assertIsNone(path)


    def test_get_thumbnails_folder(self):
        folder = self.repo.get_thumbnails_folder()
        self.assertTrue(folder.endswith("thumbnails"))


if __name__ == '__main__':
    unittest.main()
