import unittest
import sys
import os
import unicodedata
from dataclasses import asdict
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.core import (
    MediaItem,
    OptimizationState,
    IAuthService,
    IMediaRepository,
    IOptimizerService
)

class TestMediaItem(unittest.TestCase):
    """Pruebas para la entidad MediaItem"""
    
    def test_media_item_creation(self):
        """Prueba la creación de un MediaItem"""
        item = MediaItem(
            name="test.mp4",
            path="/videos/test.mp4",
            thumbnail="/thumbnails/test.jpg"
        )
        
        self.assertEqual(item.name, "test.mp4")
        self.assertEqual(item.path, "/videos/test.mp4")
        self.assertEqual(item.thumbnail, "/thumbnails/test.jpg")
    
    def test_media_item_default_values(self):
        """Prueba que no hay valores por defecto (todos son requeridos)"""
        with self.assertRaises(TypeError):
            MediaItem()  # Debería fallar porque faltan argumentos
        
        with self.assertRaises(TypeError):
            MediaItem(name="test.mp4")  # Faltan path y thumbnail
    
    def test_media_item_modification(self):
        """Prueba que los atributos son modificables"""
        item = MediaItem("test.mp4", "/path", "/thumb")
        item.name = "nuevo.mp4"
        item.path = "/nuevo/path"
        item.thumbnail = "/nuevo/thumb"
        
        self.assertEqual(item.name, "nuevo.mp4")
        self.assertEqual(item.path, "/nuevo/path")
        self.assertEqual(item.thumbnail, "/nuevo/thumb")


class TestOptimizationState(unittest.TestCase):
    """Pruebas para la entidad OptimizationState"""
    
    def test_optimization_state_creation(self):
        """Prueba la creación con valores por defecto"""
        state = OptimizationState()
        
        self.assertIsNone(state.current_video)
        self.assertEqual(state.current_step, 0)
        self.assertEqual(state.history, [])
        self.assertEqual(state.log_line, "")
        self.assertEqual(state.video_info, {})
    
    def test_optimization_state_with_values(self):
        """Prueba la creación con valores personalizados"""
        history = [{"name": "test.mp4", "status": "ok"}]
        video_info = {"resolution": "1920x1080", "codec": "h264"}
        
        state = OptimizationState(
            current_video="video.mp4",
            current_step=2,
            history=history,
            log_line="Procesando...",
            video_info=video_info
        )
        
        self.assertEqual(state.current_video, "video.mp4")
        self.assertEqual(state.current_step, 2)
        self.assertEqual(state.history, history)
        self.assertEqual(state.log_line, "Procesando...")
        self.assertEqual(state.video_info, video_info)
    
    def test_optimization_state_modification(self):
        """Prueba la modificación de atributos"""
        state = OptimizationState()
        
        state.current_video = "nuevo.mp4"
        state.current_step = 3
        state.history.append({"test": "value"})
        state.log_line = "Línea de log"
        state.video_info["resolution"] = "1280x720"
        
        self.assertEqual(state.current_video, "nuevo.mp4")
        self.assertEqual(state.current_step, 3)
        self.assertEqual(len(state.history), 1)
        self.assertEqual(state.log_line, "Línea de log")
        self.assertEqual(state.video_info["resolution"], "1280x720")
    
    def test_optimization_state_to_dict(self):
        """Prueba la conversión a diccionario usando dataclasses.asdict"""
        state = OptimizationState(
            current_video="video.mp4",
            current_step=1,
            history=[{"test": "value"}],
            log_line="log",
            video_info={"res": "1080p"}
        )
        
        state_dict = asdict(state)
        
        self.assertIsInstance(state_dict, dict)
        self.assertEqual(state_dict["current_video"], "video.mp4")
        self.assertEqual(state_dict["current_step"], 1)
        self.assertEqual(state_dict["history"][0]["test"], "value")
        self.assertEqual(state_dict["log_line"], "log")
        self.assertEqual(state_dict["video_info"]["res"], "1080p")


class TestIAuthService(unittest.TestCase):
    """Pruebas para la interfaz IAuthService"""
    
    def test_interface_cannot_be_instantiated(self):
        """Prueba que la interfaz no puede ser instanciada directamente"""
        with self.assertRaises(TypeError):
            IAuthService()  # ABC con métodos abstractos no se puede instanciar
    
    def test_concrete_implementation_must_implement_methods(self):
        """Prueba que una clase concreta debe implementar los métodos"""
        
        class IncompleteAuth(IAuthService):
            pass
        
        with self.assertRaises(TypeError):
            IncompleteAuth()  # Falta implementar login
        
        class CompleteAuth(IAuthService):
            def login(self, email, password):
                return (True, {"email": email})
        
        auth = CompleteAuth()
        result, data = auth.login("test@test.com", "pass")
        
        self.assertTrue(result)
        self.assertEqual(data["email"], "test@test.com")
    
    def test_login_method_signature(self):
        """Prueba que la implementación respeta la firma del método"""
        
        class TestAuth(IAuthService):
            def login(self, email, password):
                return (email, password)  # Solo devuelve los parámetros para verificación
        
        auth = TestAuth()
        email_result, password_result = auth.login("email@test.com", "password")
        
        # Verificar los tipos fuera de la clase
        self.assertIsInstance(email_result, str)
        self.assertIsInstance(password_result, str)
        self.assertEqual(email_result, "email@test.com")
        self.assertEqual(password_result, "password")


class TestIMediaRepository(unittest.TestCase):
    """Pruebas para la interfaz IMediaRepository"""
    
    def test_interface_cannot_be_instantiated(self):
        """Prueba que la interfaz no puede ser instanciada directamente"""
        with self.assertRaises(TypeError):
            IMediaRepository()
    
    def test_concrete_implementation_must_implement_methods(self):
        """Prueba que una clase concreta debe implementar todos los métodos"""
        
        class CompleteRepo(IMediaRepository):
            def list_content(self):
                return ([], {})
            
            def get_safe_path(self, filename):
                return "/safe/path"
        
        repo = CompleteRepo()
        movies, series = repo.list_content()
        path = repo.get_safe_path("test.mp4")
        
        self.assertEqual(movies, [])
        self.assertEqual(series, {})
        self.assertEqual(path, "/safe/path")
    
    def test_list_content_return_types(self):
        """Prueba los tipos de retorno de list_content"""
        
        class TestRepo(IMediaRepository):
            def list_content(self):
                movies = [{"name": "test.mp4"}]
                series = {"Serie1": [{"name": "ep1.mp4"}]}
                return (movies, series)
            
            def get_safe_path(self, filename):
                filename = unicodedata.normalize("NFC", filename)
                return f"/safe/{filename}"
        
        repo = TestRepo()
        movies, series = repo.list_content()
        
        self.assertIsInstance(movies, list)
        self.assertIsInstance(series, dict)
        
        path = repo.get_safe_path("test.mp4")
        self.assertEqual(path, "/safe/test.mp4")
    
    def test_get_safe_path_return_optional(self):
        """Prueba que get_safe_path puede devolver None"""
        
        class TestRepo(IMediaRepository):
            def list_content(self):
                return ([], {})
            
            def get_safe_path(self, filename):
                if filename == "invalid.mp4":
                    return None
                filename = unicodedata.normalize("NFC", filename)
                return f"/safe/{filename}"
        
        repo = TestRepo()
        
        valid_path = repo.get_safe_path("valid.mp4")
        self.assertEqual(valid_path, "/safe/valid.mp4")
        
        invalid_path = repo.get_safe_path("invalid.mp4")
        self.assertIsNone(invalid_path)


class TestIOptimizerService(unittest.TestCase):
    """Pruebas para la interfaz IOptimizerService"""
    
    def test_interface_cannot_be_instantiated(self):
        """Prueba que la interfaz no puede ser instanciada directamente"""
        with self.assertRaises(TypeError):
            IOptimizerService()
    
    def test_concrete_implementation_must_implement_methods(self):
        """Prueba que una clase concreta debe implementar todos los métodos"""
        
        class CompleteOptimizer(IOptimizerService):
            def process_file(self, file_path):
                self.last_file = file_path
            
            def process_folder(self, folder_path):
                self.last_folder = folder_path
            
            def get_status(self):
                return {"status": "ok"}
        
        optimizer = CompleteOptimizer()
        
        optimizer.process_file("test.mp4")
        self.assertEqual(optimizer.last_file, "test.mp4")
        
        optimizer.process_folder("/videos")
        self.assertEqual(optimizer.last_folder, "/videos")
        
        status = optimizer.get_status()
        self.assertEqual(status, {"status": "ok"})
    
    def test_method_signatures(self):
        """Prueba que las implementaciones respetan las firmas"""
        
        class TestOptimizer(IOptimizerService):
            def process_file(self, file_path):
                self.called_with = file_path
                return None  # No debería retornar nada
            
            def process_folder(self, folder_path):
                self.called_with = folder_path
                return None  # No debería retornar nada
            
            def get_status(self):
                return {"test": "value"}
        
        optimizer = TestOptimizer()
        
        # Verificar que process_file acepta string
        result = optimizer.process_file("/path/file.mp4")
        self.assertIsNone(result)
        
        # Verificar que process_folder acepta string
        result = optimizer.process_folder("/path")
        self.assertIsNone(result)
        
        # Verificar que get_status retorna dict
        status = optimizer.get_status()
        self.assertIsInstance(status, dict)


class TestInterfaceInheritance(unittest.TestCase):
    """Pruebas de herencia múltiple y compatibilidad"""
    
    def test_class_can_implement_multiple_interfaces(self):
        """Prueba que una clase puede implementar múltiples interfaces"""
        
        class MultiService(IMediaRepository, IOptimizerService):
            # IMediaRepository
            def list_content(self):
                return ([], {})
            
            def get_safe_path(self, filename):
                filename = unicodedata.normalize("NFC", filename)
                return f"/safe/{filename}"
            
            # IOptimizerService
            def process_file(self, file_path):
                self.file = file_path
            
            def process_folder(self, folder_path):
                self.folder = folder_path
            
            def get_status(self):
                return {"status": "multi"}
        
        service = MultiService()
        
        # Verificar métodos de IMediaRepository
        movies, series = service.list_content()
        self.assertEqual(movies, [])
        
        path = service.get_safe_path("test.mp4")
        self.assertEqual(path, "/safe/test.mp4")
        
        # Verificar métodos de IOptimizerService
        service.process_file("video.mp4")
        self.assertEqual(service.file, "video.mp4")
        
        status = service.get_status()
        self.assertEqual(status, {"status": "multi"})
    
    def test_abstract_methods_cannot_be_called(self):
        """Prueba que los métodos abstractos no pueden ser llamados directamente"""
        
        class IncompleteService(IOptimizerService):
            def process_file(self, file_path):
                pass
            
            # Falta process_folder y get_status
        
        with self.assertRaises(TypeError):
            IncompleteService()


if __name__ == '__main__':
    unittest.main()