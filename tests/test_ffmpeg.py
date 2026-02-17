import unittest
import os
import sys
import subprocess
from unittest.mock import patch, MagicMock, ANY

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

class TestFFmpegHandler(unittest.TestCase):
    
    def setUp(self):
        self.state_manager = StateManager()
        self.ffmpeg_handler = FFmpegHandler(self.state_manager)
        self.test_video = "test_video.mp4"
    
    @patch('subprocess.run')
    def test_get_video_info(self, mock_run):
        """Prueba la función get_video_info"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"format": {"size": "1048576"}, "streams": [{"codec_type": "video", "width": 1280, "height": 720, "codec_name": "h264", "pix_fmt": "yuv420p"}, {"codec_type": "audio", "codec_name": "aac"}]}'
        mock_run.return_value = mock_result
        
        info = self.ffmpeg_handler.get_video_info(self.test_video)
        
        mock_run.assert_called_once()
        self.assertEqual(info["resolution"], "1280x720")
        self.assertEqual(info["vcodec"], "h264")
        self.assertEqual(info["acodec"], "aac")
        self.assertEqual(info["size"], "1.0 MB")
    
    @patch('subprocess.Popen')
    def test_execute(self, mock_popen):
        """Prueba la función execute - CORREGIDO"""
        # Configurar el mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("salida", "error")
        mock_popen.return_value = mock_process
        
        # Llamar a la función
        cmd_args = ["ffmpeg", "-i", self.test_video, "-c", "copy", "output.mp4"]
        result = self.ffmpeg_handler.execute(cmd_args)
        
        # Verificar que se llamó a Popen (sin verificar preexec_fn)
        mock_popen.assert_called_once()
        
        # Verificar los argumentos de forma manual (ignorando preexec_fn)
        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0], cmd_args)
        self.assertEqual(kwargs['stdout'], subprocess.PIPE)
        self.assertEqual(kwargs['stderr'], subprocess.STDOUT)
        self.assertTrue(kwargs['universal_newlines'])
        self.assertEqual(kwargs['bufsize'], 1)
        
        # Verificar resultado
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()