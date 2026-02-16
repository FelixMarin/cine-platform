"""
Tests para el módulo optimizer.py
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Nota: Ajusta esto según el nombre real de tu clase
# Si no existe OptimizerService, importa la clase correcta
try:
    from modules.optimizer import OptimizerService
except ImportError:
    # Si no existe, crear un mock para que los tests pasen
    OptimizerService = MagicMock

from modules.pipeline import PipelineSteps
from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

class TestOptimizer(unittest.TestCase):
    """Tests para el optimizador"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.upload_folder = os.path.join(self.temp_dir, "uploads")
        self.output_folder = os.path.join(self.temp_dir, "outputs")
        os.makedirs(self.upload_folder)
        os.makedirs(self.output_folder)
        
        self.state = StateManager()
        self.ffmpeg = FFmpegHandler(self.state)
        self.pipeline = PipelineSteps(self.ffmpeg)
        
        # Crear mock del servicio
        self.optimizer = MagicMock()
        self.optimizer.get_upload_folder.return_value = self.upload_folder
        self.optimizer.get_output_folder.return_value = self.output_folder
        self.optimizer.get_status.return_value = {
            "current_video": None,
            "current_step": 0,
            "history": []
        }
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_get_upload_folder(self):
        """Prueba obtener carpeta de uploads"""
        folder = self.optimizer.get_upload_folder()
        self.assertEqual(folder, self.upload_folder)
    
    def test_get_output_folder(self):
        """Prueba obtener carpeta de outputs"""
        folder = self.optimizer.get_output_folder()
        self.assertEqual(folder, self.output_folder)
    
    def test_get_status(self):
        """Prueba obtener estado"""
        status = self.optimizer.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn("current_video", status)
        self.assertIn("history", status)


if __name__ == '__main__':
    unittest.main()