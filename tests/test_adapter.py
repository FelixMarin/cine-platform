import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.adapter import FFmpegOptimizerAdapter, mover_a_audiovisual

os.environ["MOVIES_FOLDER"] = "/tmp/movies"

class TestFFmpegOptimizerAdapter(unittest.TestCase):

    @patch('modules.adapter.os.makedirs')
    @patch('modules.adapter.PipelineSteps')
    @patch('modules.adapter.FFmpegHandler')
    @patch('modules.adapter.StateManager')
    def setUp(self, mock_state, mock_ffmpeg, mock_pipeline, mock_makedirs):
        mock_state.return_value = MagicMock()
        mock_ffmpeg.return_value = MagicMock()
        mock_pipeline.return_value = MagicMock()

        self.adapter = FFmpegOptimizerAdapter("/up", "/temp", "/out")

        self.mock_state_instance = mock_state.return_value
        self.mock_ffmpeg_instance = mock_ffmpeg.return_value
        self.mock_pipeline_instance = mock_pipeline.return_value

    @patch('modules.adapter.shutil.copy2')
    @patch('modules.adapter.shutil.move')
    @patch('os.remove')
    @patch('os.path.exists')
    @patch('modules.adapter.mover_a_audiovisual')
    def test_process_logic_success(self, mock_mover, mock_exists, mock_remove, mock_move, mock_copy):
        video_path = "/up/video.mp4"

        self.mock_state_instance.state.video_info = {}
        mock_exists.return_value = True
        self.mock_ffmpeg_instance.get_duration.side_effect = [100, 100]

        self.adapter._process_logic(video_path)

        self.mock_pipeline_instance.process.assert_called_once()
        mock_mover.assert_called()
        mock_remove.assert_called()

        args = self.mock_state_instance.add_history.call_args[0][0]
        self.assertEqual(args['status'], "Procesado correctamente")

    @patch('modules.adapter.shutil.copy2')
    def test_process_logic_skip_optimized(self, mock_copy):
        self.adapter._process_logic("/up/video-optimized.mp4")
        mock_copy.assert_not_called()

    @patch('modules.adapter.shutil.copy2')
    def test_process_logic_validation_error(self, mock_copy):
        video_path = "/up/video.mp4"
        self.mock_ffmpeg_instance.get_duration.side_effect = [100, 50]

        self.adapter._process_logic(video_path)

        args = self.mock_state_instance.add_history.call_args[0][0]
        self.assertIn("Error", args['status'])
        self.assertIn("Discrepancia", args['status'])

    @patch('threading.Thread')
    def test_process_file(self, mock_thread):
        self.adapter.process_file("video.mp4")
        mock_thread.assert_called_once()

    @patch('os.walk')
    @patch('threading.Thread')
    def test_process_folder(self, mock_thread, mock_walk):
        mock_walk.return_value = [("/up", [], ["v1.mp4", "v2.txt"])]

        self.adapter.process_folder("/up")

        target = mock_thread.call_args[1]['target']

        with patch.object(self.adapter, '_process_logic') as mock_logic:
            target()
            mock_logic.assert_called_once_with("/up/v1.mp4")

    def test_get_status(self):
        """Prueba get_status"""
        # Como en producción el adaptador tiene self.state (no self.state_manager)
        # Creamos un mock para self.state
        mock_state = MagicMock()
        mock_state.state = MagicMock()  # state.state
        mock_state.state.current_video = "video.mp4"
        mock_state.state.current_step = 2
        mock_state.state.log_line = "Procesando..."
        mock_state.state.history = [{"name": "test.mp4", "status": "ok"}]
        mock_state.state.video_info = {"resolution": "1920x1080"}
        
        # Asignar directamente a self.adapter.state (como espera el código real)
        self.adapter.state = mock_state
        
        # Llamar al método
        status = self.adapter.get_status()
        
        # Verificaciones
        self.assertIsInstance(status, dict)
        self.assertEqual(status['current_video'], "video.mp4")
        self.assertEqual(status['current_step'], 2)


class TestMoverAudiovisual(unittest.TestCase):

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.copy2')
    @patch('os.remove')
    def test_mover_success(self, mock_remove, mock_copy, mock_makedirs, mock_exists):
        mock_exists.return_value = True

        result = mover_a_audiovisual("/out/video.mkv")

        self.assertTrue(result)
        expected = os.path.join("/tmp/movies", "mkv", "video.mkv")
        mock_copy.assert_called_with("/out/video.mkv", expected)
        mock_remove.assert_called_with("/out/video.mkv")

    @patch('os.path.exists')
    def test_mover_no_volume(self, mock_exists):
        mock_exists.return_value = False
        result = mover_a_audiovisual("/out/video.mkv")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()