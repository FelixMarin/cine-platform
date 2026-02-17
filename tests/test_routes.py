import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open, ANY
from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.routes import create_blueprints

class TestRoutes(unittest.TestCase):
    
    def setUp(self):
        """Configurar aplicación Flask para pruebas"""
        self.app = Flask(__name__)
        self.app.secret_key = 'test_key'
        self.app.config['TESTING'] = True
        self.app.config['TEMPLATES_AUTO_RELOAD'] = False
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Crear directorio de templates temporal
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Crear templates vacíos
        for template in ['index.html', 'login.html', 'optimizer.html', 'play.html', 'admin_panel.html']:
            template_path = os.path.join(self.template_dir, template)
            if not os.path.exists(template_path):
                with open(template_path, 'w', encoding='utf-8') as f:
                    if template == 'login.html':
                        f.write('{{ error }}')
                    else:
                        f.write(f"<!-- {template} -->")
        
        self.app.template_folder = self.template_dir
        
        # Crear mocks de servicios
        self.auth_service = MagicMock()
        self.media_service = MagicMock()
        self.optimizer_service = MagicMock()
        
        # Configurar mocks
        self.auth_service.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX25hbWUiOiJ0ZXN0IiwidXNlcl9yb2xlIjoidXNlciIsImF1dGhvcml0aWVzIjpbIlJPTEVfVVNFUiJdfQ.signature"
        self.optimizer_service.get_upload_folder.return_value = "/tmp/uploads"
        self.optimizer_service.get_output_folder.return_value = "/tmp/outputs"
        self.media_service.get_thumbnails_folder.return_value = "/tmp/thumbnails"
        
        # Mock para pipeline y perfiles
        self.optimizer_service.pipeline = MagicMock()
        self.optimizer_service.pipeline.get_profiles.return_value = {
            "balanced": {"name": "Balanceado", "description": "Perfil balanceado"},
            "high_quality": {"name": "Alta Calidad", "description": "Alta calidad"}
        }
        
        # Crear blueprint
        self.bp = create_blueprints(
            self.auth_service, 
            self.media_service, 
            self.optimizer_service
        )
        self.app.register_blueprint(self.bp)
        
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Limpiar después de las pruebas"""
        import shutil
        if os.path.exists(self.template_dir):
            shutil.rmtree(self.template_dir)
    
    def login_as_user(self):
        """Helper para simular login de usuario normal"""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_role'] = 'user'
            sess['user_email'] = 'user@test.com'
    
    def login_as_admin(self):
        """Helper para simular login de admin"""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_role'] = 'admin'
            sess['user_email'] = 'admin@test.com'
    
    # ===== TESTS DE AUTENTICACIÓN =====
    
    def test_login_get(self):
        """GET /login debe renderizar template login"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
    
    def test_login_post_success(self):
        """POST /login con credenciales correctas"""
        self.auth_service.login.return_value = (True, {"user": "test"})
        
        with patch('jwt.decode') as mock_jwt_decode:
            mock_jwt_decode.return_value = {
                "user_name": "test",
                "authorities": ["ROLE_ADMIN"]
            }
            
            response = self.client.post('/login', data={
                'email': 'test@test.com',
                'password': 'password'
            }, follow_redirects=False)
        
        self.auth_service.login.assert_called_once_with('test@test.com', 'password')
        self.assertEqual(response.status_code, 302)
    
    def test_login_post_failure(self):
        """POST /login con credenciales incorrectas"""
        self.auth_service.login.return_value = (False, None)
        
        response = self.client.post('/login', data={
            'email': 'test@test.com',
            'password': 'wrong'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Credenciales incorrectas', response.data)
    
    def test_logout(self):
        """GET /logout debe limpiar sesión"""
        self.login_as_user()
        
        response = self.client.get('/logout')
        
        self.assertEqual(response.status_code, 302)
    
    # ===== TESTS DE PROTECCIÓN DE RUTAS =====
    
    def test_index_requires_login(self):
        """GET / debe redirigir si no hay sesión"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
    
    def test_index_with_login(self):
        """GET / con sesión debe renderizar template"""
        self.login_as_user()
        self.media_service.list_content.return_value = ([], {})
        
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.media_service.list_content.assert_called_once()
    
    def test_optimizer_requires_admin(self):
        """GET /optimizer debe requerir admin"""
        # Sin login
        response = self.client.get('/optimizer')
        self.assertEqual(response.status_code, 302)
        
        # Con login de usuario normal
        self.login_as_user()
        response = self.client.get('/optimizer')
        self.assertEqual(response.status_code, 403)
        
        # Con login de admin
        self.login_as_admin()
        response = self.client.get('/optimizer')
        self.assertEqual(response.status_code, 200)
    
    # ===== TESTS DE STREAMING =====
    
    def test_play_requires_login(self):
        """GET /play/<filename> debe requerir login"""
        response = self.client.get('/play/test.mp4')
        self.assertEqual(response.status_code, 302)
    
    def test_play_with_login(self):
        """GET /play/<filename> con login"""
        self.login_as_user()
        
        response = self.client.get('/play/test.mp4')
        
        self.assertEqual(response.status_code, 200)
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test')
    def test_stream_video(self, mock_file, mock_getsize, mock_exists):
        """GET /stream/<filename> debe servir video"""
        self.login_as_user()
        
        mock_exists.return_value = True
        mock_getsize.return_value = 1000000
        self.media_service.get_safe_path.return_value = "/videos/test.mp4"
        
        response = self.client.get('/stream/test.mp4')
        
        self.assertEqual(response.status_code, 206)
        self.assertIn('Content-Range', response.headers)
    
    def test_stream_video_not_found(self):
        """GET /stream/<filename> con archivo no encontrado"""
        self.login_as_user()
        
        self.media_service.get_safe_path.return_value = None
        
        response = self.client.get('/stream/test.mp4')
        
        self.assertEqual(response.status_code, 404)
    
    # ===== TESTS DE THUMBNAILS =====
    
    def test_serve_thumbnail_requires_login(self):
        """GET /thumbnails/<filename> debe requerir login"""
        response = self.client.get('/thumbnails/test.jpg')
        self.assertEqual(response.status_code, 302)
    
    def test_serve_thumbnail_jpg(self):
        """GET /thumbnails/test.jpg debe servir JPG"""
        self.login_as_user()
        
        # Crear un archivo temporal real para el thumbnail
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(b'fake image data')
            tmp_path = tmp.name
        
        try:
            # Configurar mock para que devuelva la ruta del archivo real
            self.media_service.get_thumbnails_folder.return_value = os.path.dirname(tmp_path)
            
            # Mock de send_from_directory para que sirva el archivo real
            with patch('flask.send_from_directory', wraps=self.app.send_static_file) as mock_send:
                mock_send.side_effect = lambda folder, filename: self.app.response_class(
                    open(os.path.join(folder, filename), 'rb').read()
                )
                
                response = self.client.get(f'/thumbnails/{os.path.basename(tmp_path)}')
                
                self.assertEqual(response.status_code, 200)
        finally:
            # Limpiar
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    @patch('os.path.exists')
    def test_detect_thumbnail_format(self, mock_exists):
        """GET /thumbnails/detect/<filename> debe detectar formatos"""
        self.login_as_user()
        
        def exists_side_effect(path):
            if 'test-optimized.jpg' in path:
                return True
            return False
        
        mock_exists.side_effect = exists_side_effect
        
        response = self.client.get('/thumbnails/detect/test-optimized.jpg')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['has_jpg'])
        self.assertFalse(data['has_webp'])
    
    # ===== TESTS DE API =====
    
    def test_api_movies_requires_login(self):
        """GET /api/movies debe requerir login"""
        response = self.client.get('/api/movies')
        self.assertEqual(response.status_code, 401)
    
    def test_api_movies_with_login(self):
        """GET /api/movies con login"""
        self.login_as_user()
        
        categorias = {"Acción": [{"name": "test.mp4"}]}
        series = {"Serie1": [{"name": "ep1.mp4"}]}
        self.media_service.list_content.return_value = (categorias, series)
        
        response = self.client.get('/api/movies')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('categorias', data)
        self.assertIn('series', data)
    
    def test_thumbnail_status(self):
        """GET /api/thumbnail-status debe devolver estado"""
        self.login_as_user()
        
        self.media_service.get_thumbnail_status.return_value = {
            "queue_size": 5,
            "total": 10,
            "processed": 5
        }
        
        response = self.client.get('/api/thumbnail-status')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['queue_size'], 5)
        self.assertIn('timestamp', data)
    
    # ===== TESTS DE OPTIMIZER =====
    
    def test_get_profiles(self):
        """GET /optimizer/profiles debe devolver perfiles"""
        self.login_as_admin()
        
        response = self.client.get('/optimizer/profiles')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('balanced', data)
    
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_estimate_optimization(self, mock_exists, mock_getsize):
        """POST /optimizer/estimate debe estimar tamaño"""
        self.login_as_admin()
        
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024  # 10MB
        
        self.optimizer_service.get_upload_folder.return_value = "/tmp/uploads"
        
        response = self.client.post('/optimizer/estimate', 
            json={"filepath": "test.mp4", "profile": "balanced"},
            content_type='application/json'
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('original_mb', data)
        self.assertIn('estimated_mb', data)
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"history": [{"test": "value"}]}')
    @patch('os.path.exists')
    def test_status_endpoint(self, mock_exists, mock_file):
        """GET /status debe devolver estado actual"""
        self.login_as_admin()
        mock_exists.return_value = True
        
        response = self.client.get('/status')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('current_video', data)
        self.assertIn('history', data)
    
    @patch('werkzeug.datastructures.FileStorage.save')
    @patch('werkzeug.utils.secure_filename')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_process_file_upload(self, mock_exists, mock_makedirs, mock_secure, mock_save):
        """POST /process-file debe aceptar archivos"""
        self.login_as_admin()
        mock_exists.return_value = True
        mock_makedirs.return_value = None
        mock_secure.return_value = 'test.mp4'
        mock_save.return_value = None
        
        upload_dir = "/tmp/uploads"
        self.optimizer_service.get_upload_folder.return_value = upload_dir
        
        # Crear datos de formulario correctamente
        data = {
            'profile': (None, 'balanced'),
            'video': (MagicMock(), 'test.mp4', 'video/mp4')
        }
        
        response = self.client.post('/process-file', data=data, 
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 202)
        mock_save.assert_called_once()
    
    def test_process_status(self):
        """GET /process-status debe devolver estado de cola"""
        self.login_as_admin()
        
        response = self.client.get('/process-status')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('current', data)
        self.assertIn('queue_size', data)
    
    @patch('os.path.exists')
    def test_process_folder_route(self, mock_exists):
        """POST /process debe iniciar procesamiento de carpeta"""
        self.login_as_admin()
        mock_exists.return_value = True
        
        response = self.client.post('/process', 
            json={"folder": "/videos"},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.optimizer_service.process_folder.assert_called_once_with("/videos")
    
    def test_cancel_process(self):
        """POST /cancel-process debe cancelar proceso"""
        self.login_as_admin()
        
        response = self.client.post('/cancel-process')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', data)
    
    # ===== TESTS DE ADMIN =====
    
    def test_admin_manage_requires_admin(self):
        """GET /admin/manage debe requerir admin"""
        # Sin login - debe dar 403 según la implementación
        response = self.client.get('/admin/manage')
        self.assertEqual(response.status_code, 403)
        
        # Con login de usuario normal
        self.login_as_user()
        response = self.client.get('/admin/manage')
        self.assertEqual(response.status_code, 403)
        
        # Con login de admin
        self.login_as_admin()
        response = self.client.get('/admin/manage')
        self.assertEqual(response.status_code, 200)
    
    # ===== TESTS DE DOWNLOAD =====
    
    def test_download_file(self):
        """GET /download/<filename> debe permitir descarga"""
        self.login_as_user()
        
        # Crear un archivo temporal real
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp.write(b'fake video data')
            tmp_path = tmp.name
        
        try:
            # Configurar mock para que devuelva la ruta del archivo real
            self.media_service.get_safe_path.return_value = tmp_path
            
            response = self.client.get(f'/download/{os.path.basename(tmp_path)}')
            
            self.assertEqual(response.status_code, 200)
        finally:
            # Limpiar
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_download_file_not_found(self):
        """GET /download/<filename> con archivo no encontrado"""
        self.login_as_user()
        
        self.media_service.get_safe_path.return_value = None
        
        response = self.client.get('/download/test.mp4')
        
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()