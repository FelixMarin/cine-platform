import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.state import StateManager
from modules.core import OptimizationState

class TestStateManager(unittest.TestCase):
    
    def setUp(self):
        """Configurar StateManager con archivo temporal"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.state_file = self.temp_file.name
        self.state_manager = StateManager(self.state_file)
    
    def tearDown(self):
        """Limpiar archivo temporal"""
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)
    
    # ===== TESTS DE INICIALIZACIÓN =====
    
    def test_init_creates_empty_state(self):
        """Prueba que la inicialización crea un estado vacío"""
        self.assertIsInstance(self.state_manager.state, OptimizationState)
        self.assertIsNone(self.state_manager.state.current_video)
        self.assertEqual(self.state_manager.state.current_step, 0)
        self.assertEqual(self.state_manager.state.history, [])
        self.assertEqual(self.state_manager.state.video_info, {})
        self.assertEqual(self.state_manager.state.log_line, "")
    
    def test_init_loads_existing_state(self):
        """Prueba que carga estado existente del archivo"""
        # Crear un archivo de estado previo
        test_data = {
            "current_video": "test.mp4",
            "current_step": 2,
            "history": [{"name": "test.mp4", "status": "ok"}],
            "video_info": {"resolution": "1920x1080"}
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(test_data, f)
        
        # Crear nuevo manager que debería cargar el estado
        manager = StateManager(self.state_file)
        
        self.assertEqual(manager.state.current_video, "test.mp4")
        self.assertEqual(manager.state.current_step, 2)
        self.assertEqual(len(manager.state.history), 1)
        self.assertEqual(manager.state.history[0]["name"], "test.mp4")
        self.assertEqual(manager.state.video_info["resolution"], "1920x1080")
    
    # ===== TESTS DE GUARDADO =====
    
    def test_save_creates_file(self):
        """Prueba que save() crea el archivo correctamente"""
        self.state_manager.state.current_video = "video.mp4"
        self.state_manager.state.current_step = 3
        self.state_manager.state.history.append({"test": "value"})
        self.state_manager.state.video_info = {"codec": "h264"}
        
        self.state_manager.save()
        
        # Verificar que el archivo existe y tiene los datos correctos
        self.assertTrue(os.path.exists(self.state_file))
        
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["current_video"], "video.mp4")
        self.assertEqual(data["current_step"], 3)
        self.assertEqual(data["history"][0]["test"], "value")
        self.assertEqual(data["video_info"]["codec"], "h264")
    
    @patch('modules.state.logger')
    def test_save_error_handling(self, mock_logger):
        """Prueba que save() maneja errores correctamente"""
        with patch('builtins.open', side_effect=Exception("Error de escritura")):
            self.state_manager.save()
            mock_logger.error.assert_called_once()
    
    # ===== TESTS DE CARGA =====
    
    def test_load_from_nonexistent_file(self):
        """Prueba que load() maneja archivo inexistente"""
        # Eliminar el archivo temporal
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)
        
        # Crear nuevo manager (debería tener estado vacío)
        manager = StateManager(self.state_file)
        
        self.assertIsNone(manager.state.current_video)
        self.assertEqual(manager.state.current_step, 0)
        self.assertEqual(manager.state.history, [])
    
    @patch('modules.state.logger')
    def test_load_corrupted_file(self, mock_logger):
        """Prueba que load() maneja archivos corruptos"""
        with open(self.state_file, 'w') as f:
            f.write("json inválido")
        
        manager = StateManager(self.state_file)
        
        # Debería tener estado vacío y loguear error
        self.assertIsNone(manager.state.current_video)
        mock_logger.error.assert_called_once()
    
    # ===== TESTS DE MÉTODOS DE ACTUALIZACIÓN =====
    
    def test_update_log(self):
        """Prueba update_log()"""
        self.state_manager.update_log("Línea de prueba")
        self.assertEqual(self.state_manager.state.log_line, "Línea de prueba")
    
    def test_set_current_video(self):
        """Prueba set_current_video()"""
        self.state_manager.set_current_video("video.mp4")
        
        self.assertEqual(self.state_manager.state.current_video, "video.mp4")
        
        # Verificar que se guardó en disco
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["current_video"], "video.mp4")
    
    def test_set_step(self):
        """Prueba set_step()"""
        self.state_manager.set_step(5)
        
        self.assertEqual(self.state_manager.state.current_step, 5)
        
        # Verificar en disco
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["current_step"], 5)
    
    def test_set_video_info(self):
        """Prueba set_video_info()"""
        info = {"resolution": "1280x720", "codec": "h264"}
        self.state_manager.set_video_info(info)
        
        self.assertEqual(self.state_manager.state.video_info, info)
        
        # Verificar en disco
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["video_info"]["resolution"], "1280x720")
    
    def test_add_history(self):
        """Prueba add_history()"""
        entry = {"name": "test.mp4", "status": "completado"}
        self.state_manager.add_history(entry)
        
        self.assertEqual(len(self.state_manager.state.history), 1)
        self.assertEqual(self.state_manager.state.history[0]["name"], "test.mp4")
        
        # Verificar en disco
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["name"], "test.mp4")
    
    def test_reset(self):
        """Prueba reset()"""
        # Poner algunos valores
        self.state_manager.set_current_video("video.mp4")
        self.state_manager.set_step(3)
        self.state_manager.set_video_info({"res": "1080p"})
        self.state_manager.add_history({"test": "value"})
        self.state_manager.update_log("log line")
        
        # Resetear
        self.state_manager.reset()
        
        # Verificar que se reseteó
        self.assertIsNone(self.state_manager.state.current_video)
        self.assertEqual(self.state_manager.state.current_step, 0)
        self.assertEqual(self.state_manager.state.video_info, {})
        # El historial NO se resetea (solo current)
        self.assertEqual(len(self.state_manager.state.history), 1)
        # log_line no se resetea en reset()
        self.assertEqual(self.state_manager.state.log_line, "log line")
        
        # Verificar en disco
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        
        self.assertIsNone(data["current_video"])
        self.assertEqual(data["current_step"], 0)
        self.assertEqual(data["video_info"], {})
        self.assertEqual(len(data["history"]), 1)
    
    # ===== TESTS DE COMPORTAMIENTO =====
    
    def test_multiple_updates_persist(self):
        """Prueba que múltiples actualizaciones persisten correctamente"""
        self.state_manager.set_current_video("video1.mp4")
        self.state_manager.set_step(1)
        self.state_manager.set_video_info({"res": "720p"})
        self.state_manager.add_history({"name": "video1.mp4"})
        
        self.state_manager.set_current_video("video2.mp4")
        self.state_manager.set_step(2)
        self.state_manager.set_video_info({"res": "1080p"})
        self.state_manager.add_history({"name": "video2.mp4"})
        
        # Verificar estado final
        self.assertEqual(self.state_manager.state.current_video, "video2.mp4")
        self.assertEqual(self.state_manager.state.current_step, 2)
        self.assertEqual(self.state_manager.state.video_info["res"], "1080p")
        self.assertEqual(len(self.state_manager.state.history), 2)
        
        # Verificar archivo
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["current_video"], "video2.mp4")
        self.assertEqual(data["current_step"], 2)
        self.assertEqual(len(data["history"]), 2)
    
    def test_state_immutability(self):
        """Prueba que el estado no se modifica sin llamar a métodos"""
        original_video = self.state_manager.state.current_video
        original_step = self.state_manager.state.current_step
        original_history = self.state_manager.state.history.copy()
        
        # Modificar directamente debería funcionar pero no guardar
        self.state_manager.state.current_video = "nuevo.mp4"
        
        # Recargar el manager para verificar que no se guardó
        new_manager = StateManager(self.state_file)
        
        self.assertEqual(new_manager.state.current_video, original_video)
        
        # Restaurar
        self.state_manager.state.current_video = original_video
    
    def test_history_limit(self):
        """Prueba que el historial puede crecer indefinidamente (sin límite)"""
        for i in range(100):
            self.state_manager.add_history({"index": i})
        
        self.assertEqual(len(self.state_manager.state.history), 100)
        
        # Verificar archivo
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data["history"]), 100)


class TestStateManagerEdgeCases(unittest.TestCase):
    """Pruebas de casos extremos"""
    
    def test_state_file_in_directory(self):
        """Prueba crear archivo de estado en un directorio específico"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "custom_state.json")
            manager = StateManager(state_path)
            
            manager.set_current_video("test.mp4")
            
            self.assertTrue(os.path.exists(state_path))
            
            with open(state_path, 'r') as f:
                data = json.load(f)
            self.assertEqual(data["current_video"], "test.mp4")
    
    @patch('modules.state.logger')
    def test_save_permission_error(self, mock_logger):
        """Prueba error de permisos al guardar"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "state.json")
            manager = StateManager(state_path)
            
            # Hacer el directorio de solo lectura
            os.chmod(temp_dir, 0o444)
            
            try:
                manager.set_current_video("test.mp4")
                # Debería loguear error pero no fallar
                mock_logger.error.assert_called()
            finally:
                os.chmod(temp_dir, 0o755)  # Restaurar permisos
    
    def test_load_with_missing_keys(self):
        """Prueba cargar archivo con keys faltantes"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"current_video": "test.mp4"}, f)  # Faltan otros keys
            temp_path = f.name
        
        try:
            manager = StateManager(temp_path)
            
            self.assertEqual(manager.state.current_video, "test.mp4")
            self.assertEqual(manager.state.current_step, 0)  # Default
            self.assertEqual(manager.state.history, [])      # Default
            self.assertEqual(manager.state.video_info, {})   # Default
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()