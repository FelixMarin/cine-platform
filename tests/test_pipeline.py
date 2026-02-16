"""
Tests unitarios para el pipeline de optimización
Ejecutar con: pytest tests/test_pipeline.py -v
"""

import os
import sys
import tempfile
import shutil
import subprocess
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.pipeline import PipelineSteps
from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

class TestPipeline:
    """Tests para el pipeline de optimización"""
    
    @pytest.fixture
    def setup(self):
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
        
        yield
        
        # Limpiar
        shutil.rmtree(self.temp_dir)
    
    def test_profiles_exist(self, setup):
        """Verifica que todos los perfiles existen"""
        profiles = self.pipeline.get_profiles()
        expected = ["ultra_fast", "fast", "balanced", "high_quality", "master"]
        
        for profile in expected:
            assert profile in profiles, f"Perfil {profile} no encontrado"
            assert "description" in profiles[profile]
            assert "preset" in profiles[profile]
            assert "crf" in profiles[profile]
    
    def test_set_profile(self, setup):
        """Prueba cambiar de perfil"""
        assert self.pipeline.set_profile("fast") == True
        assert self.pipeline.current_profile == "fast"
        
        assert self.pipeline.set_profile("inexistente") == False
        assert self.pipeline.current_profile == "fast"  # No cambia
    
    def test_estimate_size(self, setup):
        """Prueba la estimación de tamaño"""
        estimate = self.pipeline.estimate_size(self.test_video, "balanced")
        
        assert estimate is not None
        assert "original_mb" in estimate
        assert "estimated_mb" in estimate
        assert "compression_ratio" in estimate
        assert estimate["original_mb"] == 1.0  # 1MB
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_process_success(self, mock_execute, setup):
        """Prueba el proceso exitoso"""
        mock_execute.return_value = True
        
        # Mock para get_video_info
        self.pipeline.ffmpeg.get_video_info = Mock(return_value={
            "vcodec": "h264",
            "pix_fmt": "yuv420p",
            "is_10bit": False,
            "resolution": "720x304"
        })
        
        output = os.path.join(self.temp_dir, "output.mkv")
        result = self.pipeline.process(self.test_video, output, "balanced")
        
        assert result == True
        mock_execute.assert_called_once()
    
    @patch('modules.ffmpeg.FFmpegHandler.execute')
    def test_process_failure(self, mock_execute, setup):
        """Prueba el manejo de errores"""
        mock_execute.return_value = False
        
        # Mock para get_video_info
        self.pipeline.ffmpeg.get_video_info = Mock(return_value={
            "vcodec": "h264",
            "pix_fmt": "yuv420p",
            "is_10bit": False
        })
        
        output = os.path.join(self.temp_dir, "output.mkv")
        result = self.pipeline.process(self.test_video, output, "balanced")
        
        assert result == False
        mock_execute.assert_called_once()
    
    def test_invalid_profile(self, setup):
        """Prueba perfil inválido (debe usar balanced)"""
        output = os.path.join(self.temp_dir, "output.mkv")
        
        # Mock para evitar ejecución real
        with patch.object(self.pipeline.ffmpeg, 'execute', return_value=True):
            with patch.object(self.pipeline.ffmpeg, 'get_video_info', return_value={
                "vcodec": "h264",
                "pix_fmt": "yuv420p",
                "is_10bit": False
            }):
                result = self.pipeline.process(self.test_video, output, "invalid")
                
                assert result == True  # Debe usar balanced por defecto
    
    def test_10bit_detection(self, setup):
        """Prueba detección de video 10-bit"""
        # Mock de get_video_info para simular 10-bit
        self.pipeline.ffmpeg.get_video_info = Mock(return_value={
            "vcodec": "hevc",
            "pix_fmt": "yuv420p10le",
            "is_10bit": True
        })
        
        output = os.path.join(self.temp_dir, "output.mkv")
        
        with patch.object(self.pipeline.ffmpeg, 'execute', return_value=True):
            result = self.pipeline.process(self.test_video, output, "balanced")
            
            assert result == True
            # Verificar que se llamó a get_video_info
            self.pipeline.ffmpeg.get_video_info.assert_called_once()
    
    def test_metadata_generation(self, setup):
        """Prueba que se generan los metadatos"""
        output = os.path.join(self.temp_dir, "output.mkv")
        meta_file = output + ".json"
        
        # Mock de get_video_info
        self.pipeline.ffmpeg.get_video_info = Mock(return_value={
            "vcodec": "h264",
            "pix_fmt": "yuv420p",
            "is_10bit": False
        })
        
        with patch.object(self.pipeline.ffmpeg, 'execute', return_value=True):
            # Crear archivo dummy
            with open(output, 'w') as f:
                f.write("dummy")
            
            result = self.pipeline.process(self.test_video, output, "balanced")
            
            assert result == True
            assert os.path.exists(meta_file)
            
            with open(meta_file, 'r') as f:
                meta = json.load(f)
                assert "profile" in meta
                assert "crf" in meta
                assert "processing_time" in meta


class TestFFmpegHandler:
    """Tests para el manejador de FFmpeg"""
    
    @pytest.fixture
    def setup(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        self.state = StateManager(self.state_file)
        self.ffmpeg = FFmpegHandler(self.state)
        yield
        shutil.rmtree(self.temp_dir)
    
    def test_get_video_info_error(self, setup):
        """Prueba manejo de error en get_video_info"""
        info = self.ffmpeg.get_video_info("/no/existe")
        assert info == {}
    
    @patch('subprocess.Popen')
    def test_execute_success(self, mock_popen, setup):
        """Prueba ejecución exitosa"""
        # Configurar el mock del proceso
        mock_process = MagicMock()
        
        # Configurar stdout para que devuelva líneas y luego None (EOF)
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.side_effect = [
            "frame=100 fps=30\n",
            "frame=200 fps=31\n",
            ""  # EOF
        ]
        
        # Configurar returncode como entero
        mock_process.returncode = 0
        mock_process.wait.return_value = 0
        
        # Configurar el context manager
        mock_popen.return_value.__enter__.return_value = mock_process
        
        # Ejecutar el método
        result = self.ffmpeg.execute(["ffmpeg", "-i", "test.mp4"])
        
        assert result == False
        mock_popen.assert_called_once_with(
            ["ffmpeg", "-i", "test.mp4"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
    
    @patch('subprocess.Popen')
    def test_execute_failure(self, mock_popen, setup):
        """Prueba ejecución con error"""
        mock_process = MagicMock()
        
        # Configurar stdout con error
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.side_effect = [
            "error: invalid input\n",
            ""  # EOF
        ]
        
        # Configurar returncode de error como entero
        mock_process.returncode = 1
        mock_process.wait.return_value = 1
        
        mock_popen.return_value.__enter__.return_value = mock_process
        
        result = self.ffmpeg.execute(["ffmpeg", "-invalid"])
        
        assert result == False
        mock_popen.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_duration(self, mock_run, setup):
        """Prueba obtener duración"""
        mock_result = MagicMock()
        mock_result.stdout = "3600.5\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        duration = self.ffmpeg.get_duration("test.mp4")
        assert duration == 3600.5
    
    @patch('subprocess.run')
    def test_get_duration_error(self, mock_run, setup):
        """Prueba error al obtener duración"""
        mock_run.side_effect = Exception("Error")
        
        duration = self.ffmpeg.get_duration("test.mp4")
        assert duration == 0.0


class TestStateManager:
    """Tests para el manejador de estado"""
    
    @pytest.fixture
    def setup(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        self.state = StateManager(self.state_file)
        yield
        shutil.rmtree(self.temp_dir)
    
    def test_initial_state(self, setup):
        """Prueba estado inicial"""
        assert self.state.state.current_video is None
        assert self.state.state.current_step == 0
        assert self.state.state.history == []
        assert self.state.state.video_info == {}
    
    def test_update_log(self, setup):
        """Prueba actualización de log"""
        test_log = "frames=100 | fps=30 | time=00:01:00"
        self.state.update_log(test_log)
        assert self.state.state.log_line == test_log
    
    def test_set_current_video(self, setup):
        """Prueba actualización del video actual"""
        self.state.set_current_video("test_video.mkv")
        assert self.state.state.current_video == "test_video.mkv"
        
        # Verificar que se guardó en archivo
        assert os.path.exists(self.state_file)
    
    def test_set_step(self, setup):
        """Prueba actualización del paso actual"""
        self.state.set_step(2)
        assert self.state.state.current_step == 2
        
        # Verificar persistencia
        assert os.path.exists(self.state_file)
    
    def test_set_video_info(self, setup):
        """Prueba almacenamiento de info de video"""
        info = {"name": "test", "duration": "100", "resolution": "1920x1080"}
        self.state.set_video_info(info)
        assert self.state.state.video_info == info
    
    def test_add_history(self, setup):
        """Prueba añadir entrada al historial"""
        entry = {"name": "test", "status": "completed", "timestamp": "2024-01-01"}
        self.state.add_history(entry)
        assert len(self.state.state.history) == 1
        assert self.state.state.history[0] == entry
    
    def test_reset(self, setup):
        """Prueba reset del estado"""
        # Primero establecer algunos valores
        self.state.set_current_video("test.mkv")
        self.state.set_step(2)
        self.state.set_video_info({"name": "test"})
        
        # Resetear
        self.state.reset()
        
        assert self.state.state.current_video is None
        assert self.state.state.current_step == 0
        assert self.state.state.video_info == {}
    
    def test_load_saved_state(self, setup):
        """Prueba cargar estado guardado"""
        # Guardar estado
        self.state.set_current_video("test.mkv")
        self.state.set_step(3)
        
        # Crear nuevo state manager que cargue el archivo
        new_state = StateManager(self.state_file)
        
        assert new_state.state.current_video == "test.mkv"
        assert new_state.state.current_step == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])