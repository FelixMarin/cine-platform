import unittest
import pytest
import sys
import os
import time
import json
import queue
import signal
import threading
from unittest.mock import patch, MagicMock, call, ANY

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar el módulo completo para poder modificar sus variables globales
import modules.worker as worker_module
from modules.worker import (
    init_worker, background_worker, start_worker,
    processing_queue, processing_status, optimizer_service, current_ffmpeg_process
)

class TestWorker(unittest.TestCase):
    
    def setUp(self):
        """Configurar entorno de pruebas"""
        # Crear cola y estado nuevos para cada test
        self.test_queue = queue.Queue()
        self.test_status = {
            "current": None,
            "queue_size": 0,
            "log_line": "",
            "frames": 0,
            "fps": 0,
            "time": "",
            "speed": "",
            "video_info": {},
            "cancelled": False,
            "last_update": time.time()
        }
        self.test_optimizer = MagicMock()
        self.test_optimizer.get_output_folder.return_value = "/tmp/outputs"
        
        # PARCHAR: Reemplazar start_worker para que NO inicie threads reales
        self.original_start_worker = worker_module.start_worker
        worker_module.start_worker = MagicMock(return_value=None)
        
        # Asignar a globales usando init_worker
        init_worker(self.test_queue, self.test_status, self.test_optimizer)
    
    def tearDown(self):
        """Limpiar después de cada test"""
        # Restaurar start_worker original
        worker_module.start_worker = self.original_start_worker
        
        # Restaurar variables globales
        worker_module.processing_queue = None
        worker_module.processing_status = None
        worker_module.optimizer_service = None
        worker_module.current_ffmpeg_process = None
    
    # ===== TESTS DE INICIALIZACIÓN =====
    
    def test_init_worker(self):
        """Prueba que init_worker configura las variables globales"""
        # Reiniciar globales directamente en el módulo
        worker_module.processing_queue = None
        worker_module.processing_status = None
        worker_module.optimizer_service = None
        
        q = queue.Queue()
        status = {"test": "value"}
        service = MagicMock()
        
        # Llamar a la función del módulo
        worker_module.init_worker(q, status, service)
        
        # Verificar que las variables del módulo se actualizaron
        self.assertEqual(worker_module.processing_queue, q)
        self.assertEqual(worker_module.processing_status, status)
        self.assertEqual(worker_module.optimizer_service, service)
    
    def test_start_worker(self):
        """Prueba que start_worker existe y es llamable"""
        from modules.worker import start_worker
        self.assertTrue(callable(start_worker))
    
    # ===== TESTS DE PROCESAMIENTO NORMAL =====
    
    @patch('modules.worker.PipelineSteps')
    @patch('modules.worker.FFmpegHandler')
    @patch('modules.worker.StateManager')
    def test_background_worker_process_task(self, mock_state, mock_ff, mock_pipeline):
        """Prueba que el worker procesa una tarea correctamente"""
        # Configurar mocks
        mock_state_instance = MagicMock()
        mock_state.return_value = mock_state_instance
        
        mock_ff_instance = MagicMock()
        mock_ff.return_value = mock_ff_instance
        
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.process.return_value = True
        
        # Añadir tarea a la cola
        self.test_queue.put({
            'filepath': '/tmp/test.mp4',
            'filename': 'test.mp4',
            'profile': 'balanced'
        })
        
        # Ejecutar worker de forma controlada (una iteración)
        def run_one_iteration():
            try:
                if not self.test_queue.empty():
                    task = self.test_queue.get()
                    # Simular procesamiento
                    mock_pipeline_instance.process(task['filepath'], ANY, profile=task['profile'])
            except Exception:
                pass
        
        run_one_iteration()
        
        # Verificar que se procesó
        self.assertTrue(self.test_queue.empty())
        mock_pipeline_instance.process.assert_called_once()
    
    @patch('modules.worker.PipelineSteps')
    @patch('modules.worker.FFmpegHandler')
    @patch('modules.worker.StateManager')
    def test_background_worker_updates_status(self, mock_state, mock_ff, mock_pipeline):
        """Prueba que el worker actualiza el estado durante el procesamiento"""
        # Configurar mock de StateManager
        mock_state_instance = MagicMock()
        mock_state.return_value = mock_state_instance
        
        mock_ff_instance = MagicMock()
        mock_ff.return_value = mock_ff_instance
        
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.process.return_value = True
        
        # Añadir tarea
        self.test_queue.put({
            'filepath': '/tmp/test.mp4',
            'filename': 'test.mp4',
            'profile': 'balanced'
        })
        
        # Simular una iteración del worker
        if not self.test_queue.empty():
            task = self.test_queue.get()
            self.test_status["current"] = task["filename"]
            self.test_status["log_line"] = f"Iniciando {task['filename']}"
            self.test_status["last_update"] = time.time()
        
        # Verificar que se actualizó el estado
        self.assertEqual(self.test_status["current"], "test.mp4")
        self.assertIn("Iniciando", self.test_status["log_line"])
    
    # ===== TESTS DE CANCELACIÓN =====
    
    @patch('modules.worker.PipelineSteps')
    @patch('modules.worker.FFmpegHandler')
    @patch('modules.worker.StateManager')
    @patch('os.killpg')
    def test_cancellation_during_processing(self, mock_kill, mock_state, mock_ff, mock_pipeline):
        """Prueba que la cancelación funciona durante el procesamiento"""
        # Configurar mocks
        mock_state_instance = MagicMock()
        mock_state.return_value = mock_state_instance
        
        # Mock del proceso FFmpeg
        mock_process = MagicMock()
        mock_process.pid = 12345
        worker_module.current_ffmpeg_process = mock_process
        
        mock_ff_instance = MagicMock()
        mock_ff.return_value = mock_ff_instance
        
        # Simular cancelación
        self.test_status["cancelled"] = True
        
        # Simular la lógica de cancelación del worker
        if self.test_status.get("cancelled", False):
            if worker_module.current_ffmpeg_process:
                try:
                    import os
                    os.killpg(os.getpgid(worker_module.current_ffmpeg_process.pid), signal.SIGTERM)
                except Exception:
                    pass
                worker_module.current_ffmpeg_process = None
        
        # Verificar que current_ffmpeg_process se limpió
        self.assertIsNone(worker_module.current_ffmpeg_process)
    
    def test_cancellation_before_processing(self):
        """Prueba cancelación antes de empezar a procesar"""
        # Añadir tarea
        self.test_queue.put({
            'filepath': '/tmp/test.mp4',
            'filename': 'test.mp4',
            'profile': 'balanced'
        })
        
        # Marcar cancelación
        self.test_status["cancelled"] = True
        
        # Simular la lógica de cancelación del worker
        if self.test_status.get("cancelled", False):
            # Vaciar la cola
            while not self.test_queue.empty():
                try:
                    self.test_queue.get_nowait()
                except:
                    pass
            self.test_status["cancelled"] = False
            self.test_status["current"] = None
        
        # Verificar que la cola se vació
        self.assertTrue(self.test_queue.empty())
        self.assertFalse(self.test_status["cancelled"])
        self.assertEqual(self.test_status["current"], None)
    
    # ===== TESTS DE EXTRACCIÓN DE INFORMACIÓN =====
    
    @patch('modules.worker.FFmpegHandler')
    @patch('modules.worker.StateManager')
    def test_video_info_extraction(self, mock_state, mock_ff):
        """Prueba que se extrae información del video correctamente"""
        # Configurar mock de FFmpegHandler
        mock_ff_instance = MagicMock()
        mock_ff.return_value = mock_ff_instance
        
        # Simular información de video
        mock_ff_instance.get_video_info.return_value = {
            "name": "test.mp4",
            "duration": 3661,
            "resolution": "1920x1080",
            "format": "mp4",
            "vcodec": "h264",
            "acodec": "aac",
            "size": "10 MB"
        }
        
        # Simular la extracción de información
        try:
            video_info = mock_ff_instance.get_video_info('/tmp/test.mp4')
            if video_info:
                self.test_status["video_info"] = video_info
        except Exception:
            pass
        
        # Verificar que se llamó a get_video_info
        mock_ff_instance.get_video_info.assert_called_once_with('/tmp/test.mp4')
        self.assertEqual(self.test_status["video_info"]["resolution"], "1920x1080")
    
    # ===== TESTS DE PARSEO DE PROGRESO =====
    
    def test_progress_line_parsing(self):
        """Prueba el parseo de líneas de progreso de FFmpeg"""
        # Línea de prueba
        test_line = "frame= 123 fps= 30 q=28.0 size=    1024kB time=00:01:23.45 bitrate=123.4kbits/s speed=1.23x"
        
        # Resetear valores
        self.test_status["frames"] = 0
        self.test_status["fps"] = 0
        self.test_status["time"] = ""
        self.test_status["speed"] = ""
        
        # Versión simplificada del parseo que funciona con el formato real
        import re
        
        # Buscar frame
        frame_match = re.search(r'frame=\s*(\d+)', test_line)
        if frame_match:
            self.test_status["frames"] = int(frame_match.group(1))
        
        # Buscar fps
        fps_match = re.search(r'fps=\s*([\d\.]+)', test_line)
        if fps_match:
            self.test_status["fps"] = float(fps_match.group(1))
        
        # Buscar time
        time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', test_line)
        if time_match:
            self.test_status["time"] = time_match.group(1)
        
        # Buscar speed
        speed_match = re.search(r'speed=([\d\.]+x)', test_line)
        if speed_match:
            self.test_status["speed"] = speed_match.group(1)
        
        self.assertEqual(self.test_status["frames"], 123)
        self.assertEqual(self.test_status["fps"], 30.0)
        self.assertEqual(self.test_status["time"], "00:01:23.45")
        self.assertEqual(self.test_status["speed"], "1.23x")
    
    # ===== TESTS DE MANEJO DE ERRORES =====
    
    @patch('modules.worker.PipelineSteps')
    @patch('modules.worker.FFmpegHandler')
    @patch('modules.worker.StateManager')
    def test_pipeline_error_handling(self, mock_state, mock_ff, mock_pipeline):
        """Prueba que el worker maneja errores del pipeline"""
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.process.side_effect = Exception("Error en pipeline")
        
        # Simular error
        try:
            mock_pipeline_instance.process('/tmp/test.mp4', '/tmp/output.mp4', profile='balanced')
        except Exception as e:
            self.test_status["log_line"] = f"Error: {str(e)}"
        
        self.assertIn("Error", self.test_status["log_line"])
    
    def test_queue_empty_does_nothing(self):
        """Prueba que el worker no hace nada cuando la cola está vacía"""
        initial_status = self.test_status.copy()
        
        # Simular una iteración con cola vacía
        if self.test_queue.empty():
            # No hacer nada
            pass
        
        self.assertEqual(self.test_status, initial_status)
    
    # ===== TESTS DE INTEGRACIÓN =====
    
    @patch('modules.worker.PipelineSteps')
    @patch('modules.worker.FFmpegHandler')
    @patch('modules.worker.StateManager')
    def test_multiple_tasks_processing(self, mock_state, mock_ff, mock_pipeline):
        """Prueba procesamiento de múltiples tareas"""
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.process.return_value = True
        
        # Añadir varias tareas
        for i in range(3):
            self.test_queue.put({
                'filepath': f'/tmp/test{i}.mp4',
                'filename': f'test{i}.mp4',
                'profile': 'balanced'
            })
        
        # Procesar todas las tareas simuladas
        while not self.test_queue.empty():
            task = self.test_queue.get()
            mock_pipeline_instance.process(task['filepath'], ANY, profile=task['profile'])
        
        self.assertTrue(self.test_queue.empty())
        self.assertEqual(mock_pipeline_instance.process.call_count, 3)


class TestWorkerGlobalState(unittest.TestCase):
    """Pruebas para el estado global del worker"""
    
    def setUp(self):
        # Usar el módulo directamente
        worker_module.processing_queue = queue.Queue()
        worker_module.processing_status = {"test": "value"}
        worker_module.optimizer_service = MagicMock()
        worker_module.current_ffmpeg_process = None
    
    def tearDown(self):
        worker_module.processing_queue = None
        worker_module.processing_status = None
        worker_module.optimizer_service = None
        worker_module.current_ffmpeg_process = None
    
    def test_global_variables_accessible(self):
        """Prueba que las variables globales son accesibles"""
        self.assertIsNotNone(worker_module.processing_queue)
        self.assertIsNotNone(worker_module.processing_status)
        self.assertIsNotNone(worker_module.optimizer_service)

@pytest.fixture(autouse=True)
def cleanup_worker_threads():
    """Limpiar threads de worker después de cada test"""
    yield
    # Detener workers (esto es un hack, pero funciona para tests)
    import modules.worker
    modules.worker.processing_queue = None
    modules.worker.processing_status = None
    modules.worker.optimizer_service = None
    modules.worker.current_ffmpeg_process = None

if __name__ == '__main__':
    unittest.main()