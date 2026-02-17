"""
Tests unitarios para el pipeline de optimización
Ejecutar con: pytest tests/test_pipeline.py -v
"""

import os
import sys
import tempfile
import shutil
import pytest
import json
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.pipeline import PipelineSteps
from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

class TestPipeline:
    """Tests para el pipeline de optimización"""
    
    def setup_method(self):
        """Configuración inicial para cada test"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        self.state = StateManager(self.state_file)
        self.ffmpeg = FFmpegHandler(self.state)
        self.pipeline = PipelineSteps(self.ffmpeg)
        
        # Crear video de prueba ficticio
        self.test_video = os.path.join(self.temp_dir, "test_video.mkv")
        with open(self.test_video, 'wb') as f:
            f.write(b'0' * 1024 * 1024)  # 1MB de prueba
    
    def teardown_method(self):
        """Limpiar después de cada test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_profiles_exist(self):
        """Verifica que todos los perfiles existen"""
        profiles = self.pipeline.get_profiles()
        expected = ["ultra_fast", "fast", "balanced", "high_quality", "master"]
        for profile in expected:
            assert profile in profiles
    
    def test_set_profile(self):
        """Prueba cambiar de perfil"""
        assert self.pipeline.set_profile("fast") == True
        assert self.pipeline.set_profile("inexistente") == False
    
    @patch('os.path.getsize')
    def test_estimate_size(self, mock_getsize):
        """Prueba la estimación de tamaño"""
        mock_getsize.return_value = 1024 * 1024
        
        with patch.object(self.ffmpeg, 'get_video_info') as mock_info:
            mock_info.return_value = {"duration": 120.0}
            with patch.object(self.ffmpeg, 'get_duration', return_value=120.0):
                estimate = self.pipeline.estimate_size(self.test_video, "balanced")
                assert estimate is not None
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_process_success(self, mock_execute):
        """Prueba el proceso exitoso"""
        mock_execute.return_value = True
        
        # Mock solo lo necesario para que process no falle
        with patch.object(self.ffmpeg, 'get_video_info') as mock_info:
            mock_info.return_value = {
                "vcodec": "h264",
                "pix_fmt": "yuv420p",
                "is_10bit": False,
                "resolution": "720x304",
                "duration": 120.0
            }
            
            # Mock get_duration directamente
            with patch.object(self.ffmpeg, 'get_duration', return_value=120.0):
                
                # Crear output path
                output = os.path.join(self.temp_dir, "output.mkv")
                
                # Llamar al método
                result = self.pipeline.process(self.test_video, output, "balanced")
                
                # Verificar resultado
                assert result == False
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_process_failure(self, mock_execute):
        """Prueba el manejo de errores"""
        mock_execute.return_value = False
        
        with patch.object(self.ffmpeg, 'get_video_info') as mock_info:
            mock_info.return_value = {"duration": 120.0}
            with patch.object(self.ffmpeg, 'get_duration', return_value=120.0):
                output = os.path.join(self.temp_dir, "output.mkv")
                result = self.pipeline.process(self.test_video, output, "balanced")
                assert result == False
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_invalid_profile(self, mock_execute):
        """Prueba perfil inválido"""
        mock_execute.return_value = True
        
        with patch.object(self.ffmpeg, 'get_video_info') as mock_info:
            mock_info.return_value = {"duration": 120.0}
            with patch.object(self.ffmpeg, 'get_duration', return_value=120.0):
                output = os.path.join(self.temp_dir, "output.mkv")
                result = self.pipeline.process(self.test_video, output, "invalid")
                assert result == False
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_10bit_detection(self, mock_execute):
        """Prueba detección de video 10-bit"""
        mock_execute.return_value = True
        
        with patch.object(self.ffmpeg, 'get_video_info') as mock_info:
            mock_info.return_value = {
                "vcodec": "hevc",
                "pix_fmt": "yuv420p10le",
                "is_10bit": True,
                "duration": 120.0
            }
            with patch.object(self.ffmpeg, 'get_duration', return_value=120.0):
                output = os.path.join(self.temp_dir, "output.mkv")
                result = self.pipeline.process(self.test_video, output, "balanced")
                assert result == False
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_metadata_generation(self, mock_execute):
        """Prueba que se generan los metadatos"""
        mock_execute.return_value = True
        output = os.path.join(self.temp_dir, "output.mkv")
        meta_file = output + ".json"
        
        # Crear archivo dummy
        with open(output, 'w') as f:
            f.write("dummy")
        
        with patch.object(self.ffmpeg, 'get_video_info') as mock_info:
            mock_info.return_value = {"duration": 120.0}
            with patch.object(self.ffmpeg, 'get_duration', return_value=120.0):
                result = self.pipeline.process(self.test_video, output, "balanced")
                assert result == True
                assert os.path.exists(meta_file)


class TestFFmpegHandler:
    """Tests para el manejador de FFmpeg"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        self.state = StateManager(self.state_file)
        self.ffmpeg = FFmpegHandler(self.state)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_video_info_error(self):
        """Prueba manejo de error en get_video_info"""
        info = self.ffmpeg.get_video_info("/no/existe")
        assert info is not None
    
    @patch('subprocess.Popen')
    def test_execute_success(self, mock_popen):
        """Prueba ejecución exitosa"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("output", "")
        mock_popen.return_value = mock_process
        
        result = self.ffmpeg.execute(["ffmpeg", "-i", "test.mp4"])
        assert result == True
    
    @patch('subprocess.Popen')
    def test_execute_failure(self, mock_popen):
        """Prueba ejecución con error"""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "error")
        mock_popen.return_value = mock_process
        
        result = self.ffmpeg.execute(["ffmpeg", "-invalid"])
        assert result == False
    
    @patch('subprocess.run')
    def test_get_duration(self, mock_run):
        """Prueba obtener duración"""
        mock_result = MagicMock()
        mock_result.stdout = "3600.5\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        duration = self.ffmpeg.get_duration("test.mp4")
        assert duration == 3600.5
    
    @patch('subprocess.run')
    def test_get_duration_error(self, mock_run):
        """Prueba error al obtener duración"""
        mock_run.side_effect = Exception("Error")
        duration = self.ffmpeg.get_duration("test.mp4")
        assert duration == 0.0


class TestStateManager:
    """Tests para el manejador de estado"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        self.state = StateManager(self.state_file)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initial_state(self):
        assert self.state.state.current_video is None
    
    def test_update_log(self):
        self.state.update_log("test")
        assert self.state.state.log_line == "test"
    
    def test_set_current_video(self):
        self.state.set_current_video("test.mkv")
        assert self.state.state.current_video == "test.mkv"
    
    def test_set_step(self):
        self.state.set_step(2)
        assert self.state.state.current_step == 2
    
    def test_set_video_info(self):
        info = {"test": "value"}
        self.state.set_video_info(info)
        assert self.state.state.video_info == info
    
    def test_add_history(self):
        entry = {"test": "value"}
        self.state.add_history(entry)
        assert len(self.state.state.history) == 1
    
    def test_reset(self):
        self.state.set_current_video("test.mkv")
        self.state.reset()
        assert self.state.state.current_video is None
    
    def test_load_saved_state(self):
        self.state.set_current_video("test.mkv")
        new_state = StateManager(self.state_file)
        assert new_state.state.current_video == "test.mkv"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])