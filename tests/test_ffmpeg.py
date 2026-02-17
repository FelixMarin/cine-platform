import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

class TestFFmpegHandler(unittest.TestCase):
    
    def setUp(self):
        self.state_manager = StateManager()
        self.ffmpeg_handler = FFmpegHandler(self.state_manager)
        self.test_video = "test_video.mp4"  # Reemplazar con un archivo de prueba real
    
    @patch('subprocess.run')
    def test_get_video_info(self, mock_run):
        """Prueba la función get_video_info"""
        # Configurar el mock para que devuelva un resultado simulado
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"format": {"size": "1048576"}, "streams": [{"codec_type": "video", "width": 1280, "height": 720, "codec_name": "h264", "pix_fmt": "yuv420p"}, {"codec_type": "audio", "codec_name": "aac"}]}'  # Simular salida JSON
        mock_run.return_value = mock_result
        
        # Llamar a la función
        info = self.ffmpeg_handler.get_video_info(self.test_video)
        
        # Verificar que se llamó a subprocess.run con los argumentos correctos
        mock_run.assert_called_once()
        
        # Verificar que la información se parseó correctamente
        self.assertEqual(info["resolution"], "1280x720")
        self.assertEqual(info["vcodec"], "h264")
        self.assertEqual(info["acodec"], "aac")
        self.assertEqual(info["size"], "1.00 MB")
    
    @patch('subprocess.Popen')
    def test_execute(self, mock_popen):
        """Prueba la función execute"""
        # Configurar el mock para que devuelva un resultado exitoso
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout.return_value = iter(["line1\n", "line2\n"])  # Simular salida del proceso
        mock_popen.return_value = mock_process
    
        # Llamar a la función
        cmd_args = ["ffmpeg", "-i", self.test_video, "-c", "copy", "output.mp4"]
        result = self.ffmpeg_handler.execute(cmd_args)
    
        # Verificar que se llamó a subprocess.Popen con los argumentos correctos
        mock_popen.assert_called_once_with(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
    
        # Verificar que la función devuelve True en caso de éxito
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
