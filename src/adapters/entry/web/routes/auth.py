"""
Adaptador de entrada - Rutas de autenticación
Blueprint para /api/auth y login
"""
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for
import os
import base64
import json
import logging

from src.core.use_cases.auth import LoginUseCase, LogoutUseCase
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.config.dependencies import get_oauth_service

# Logger global
logger = None


def _get_logger():
    """Obtener o crear el logger"""
    global logger
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    return logger


def setup_logging(log_folder):
    """Setup de logging - se configurará después"""
    return _get_logger()


auth_bp = Blueprint('auth', __name__)

# Blueprint para la página principal (sin prefijo)
main_page_bp = Blueprint('main_page', __name__)


@main_page_bp.route('/status')
def status():
    """Estado de la API"""
    return jsonify({'status': 'ok'})


@main_page_bp.route('/')
@require_auth
def index():
    """Página principal del catálogo"""
    return render_template('index.html')


@main_page_bp.route('/favicon.ico')
def favicon():
    """Favicon"""
    from flask import send_from_directory
    static_dir = os.path.join(os.getcwd(), 'static')
    return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# Casos de uso inyectados
_login_use_case = None
_logout_use_case = None


def init_auth_routes(
    login_use_case: LoginUseCase = None,
    logout_use_case: LogoutUseCase = None
):
    """Inicializa los casos de uso para las rutas de autenticación"""
    global _login_use_case, _logout_use_case
    _login_use_case = login_use_case
    _logout_use_case = logout_use_case


def get_user_id():
    """Obtiene el ID del usuario de la sesión"""
    return session.get('user_id', 0)


def is_logged_in():
    """Verifica si el usuario está logueado"""
    return session.get('logged_in', False)


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Endpoint de login"""
    global _login_use_case
    
    _get_logger().info(f"[API LOGIN] Intento de login - LoginUseCase: {_login_use_case}")
    
    if _login_use_case is None:
        _get_logger().error("[API LOGIN] LoginUseCase no inicializado")
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email y password son requeridos'}), 400
        
        _get_logger().info(f"[API LOGIN] Email: {email}")
        
        success, user_data = _login_use_case.execute(email, password)
        
        if success:
            # Guardar en sesión
            session['logged_in'] = True
            session['user_id'] = user_data.get('id')
            session['email'] = user_data.get('email')
            session['username'] = user_data.get('username')
            session['user_role'] = user_data.get('role', 'admin')
            
            _get_logger().info(f"[API LOGIN] Login exitoso para: {email}")
            
            return jsonify({
                'success': True,
                'user': user_data
            })
        else:
            _get_logger().warning(f"[API LOGIN] Credenciales incorrectas para: {email}")
            return jsonify({
                'success': False,
                'error': 'Credenciales inválidas'
            }), 401
    
    except Exception as e:
        _get_logger().error(f"[API LOGIN] Error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Endpoint de logout"""
    global _logout_use_case
    
    if _logout_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        user_id = get_user_id()
        _logout_use_case.execute(user_id)
        
        # Limpiar sesión
        session.clear()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Verifica el estado de autenticación"""
    if is_logged_in():
        return jsonify({
            'logged_in': True,
            'user_id': session.get('user_id'),
            'email': session.get('email'),
            'username': session.get('username')
        })
    else:
        return jsonify({'logged_in': False})


@auth_bp.route('/api/auth/token', methods=['POST'])
def verify_token():
    """Verifica un token de autenticación"""
    global _login_use_case
    
    if _login_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token es requerido'}), 400
        
        user_data = _login_use_case.verify_token(token)
        
        if user_data:
            return jsonify({
                'valid': True,
                'user': user_data
            })
        else:
            return jsonify({'valid': False}), 401
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================
#  RUTAS DE PÁGINAS HTML
# ============================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    """Página de login - GET muestra formulario OAuth2, POST es fallback"""
    if request.method == 'GET':
        if is_logged_in():
            return redirect(url_for('main_page.index'))
        
        # Función auxiliar para decodificar base64
        def decode_b64(value, default):
            if not value:
                return default
            try:
                return base64.b64decode(value).decode('utf-8').rstrip('/')
            except:
                return default
        
        # Obtener y decodificar valores base64
        oauth2_url = decode_b64(
            os.environ.get('PUBLIC_OAUTH2_URL'), 
            'http://localhost:8080'
        )
        
        client_id = os.environ.get('OAUTH2_CLIENT_ID', 'cine-platform')
        
        client_secret = decode_b64(
            os.environ.get('OAUTH2_CLIENT_SECRET'), 
            'cine-platform-secret'
        )
        
        redirect_uri = decode_b64(
            os.environ.get('PUBLIC_REDIRECT_URI'), 
            'http://localhost:5000/oauth/callback'
        )
        
        # Logging para depuración
        _get_logger().info(f"PUBLIC_OAUTH2_URL decodificada: {oauth2_url}")
        _get_logger().info(f"OAUTH2_CLIENT_ID: {client_id}")
        _get_logger().info(f"PUBLIC_REDIRECT_URI decodificada: {redirect_uri}")
        
        return render_template('login.html', 
                              oauth2_url=oauth2_url,
                              client_id=client_id,
                              client_secret=client_secret,
                              redirect_uri=redirect_uri)
    
    # POST - Procesar login (fallback para desarrollo)
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('login.html', error='Email y contraseña requeridos')
        
        _get_logger().info(f"[LOGIN] Intento de login para usuario: {email}")
        
        # Intentar OAuth2 primero
        oauth_service = get_oauth_service()
        
        if oauth_service:
            try:
                success, user_data = oauth_service.login(email, password)
                if success:
                    session['logged_in'] = True
                    session['user_id'] = 1
                    session['email'] = email
                    session['username'] = user_data.get('username', email)
                    session['user_role'] = 'admin'
                    session['oauth_token'] = oauth_service.token
                    _get_logger().info(f"[LOGIN] OAuth exitoso para: {email}")
                    return redirect(url_for('main_page.index'))
                # OAuth2 falló, intentar fallback
            except Exception as oauth_error:
                _get_logger().warning(f"[LOGIN] OAuth falló: {oauth_error}")
                # OAuth2 no disponible, usar fallback
                pass
        
        # Fallback a credenciales locales (útil para desarrollo)
        valid_user = os.environ.get('APP_USER', 'admin')
        valid_pass = os.environ.get('APP_PASSWORD', 'Admin1')
        
        _get_logger().info(f"[LOGIN] Verificando credenciales locales: {email} == {valid_user}")
        
        if email == valid_user and password == valid_pass:
            session['logged_in'] = True
            session['user_id'] = 1
            session['email'] = email
            session['username'] = email
            session['user_role'] = 'admin'
            _get_logger().info(f"[LOGIN] Login exitoso para: {email}")
            return redirect(url_for('main_page.index'))
        else:
            _get_logger().warning(f"[LOGIN] Credenciales incorrectas para: {email}")
            return render_template('login.html', error='Credenciales incorrectas')
            
    except Exception as e:
        _get_logger().error(f"[LOGIN] Error: {e}")
        return render_template('login.html', error=f'Error: {str(e)}')


@auth_bp.route('/auth/callback', methods=['POST'])
def oauth_callback():
    """
    Callback de OAuth2 - Intercambia código por token
    """
    try:
        data = request.get_json()
        code = data.get('code')
        code_verifier = data.get('code_verifier')
        
        if not code or not code_verifier:
            _get_logger().warning("[OAUTH_CALLBACK] Código o verifier faltante")
            return jsonify({'success': False, 'error': 'Código o verifier faltante'}), 400
        
        _get_logger().info("[OAUTH_CALLBACK] Intercambiando código por token")
        
        # Obtener servicio OAuth
        oauth_service = get_oauth_service()
        
        if not oauth_service:
            _get_logger().error("[OAUTH_CALLBACK] Servicio OAuth no disponible")
            return jsonify({'success': False, 'error': 'Servicio OAuth no disponible'}), 500
        
        # Intercambiar código por token
        success, token_data = oauth_service.exchange_code_for_token(code, code_verifier)
        
        if not success:
            _get_logger().error(f"[OAUTH_CALLBACK] Error intercambiando código: {token_data}")
            return jsonify({'success': False, 'error': token_data.get('error', 'Error desconocido')}), 400
        
        # Obtener información del usuario
        access_token = token_data.get('access_token')
        user_info = oauth_service.get_userinfo(access_token)
        
        # Guardar en sesión
        session['logged_in'] = True
        session['user_id'] = user_info.get('sub', 1) if user_info else 1
        session['email'] = user_info.get('email', '') if user_info else ''
        session['username'] = user_info.get('preferred_username', user_info.get('name', 'user')) if user_info else 'user'
        session['user_role'] = 'admin'
        session['oauth_token'] = access_token
        session['oauth_refresh_token'] = token_data.get('refresh_token')
        
        _get_logger().info(f"[OAUTH_CALLBACK] Login OAuth2 exitoso para: {session.get('username')}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        _get_logger().error(f"[OAUTH_CALLBACK] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/oauth/callback', methods=['GET'])
def oauth_callback_redirect():
    """
    Callback de OAuth2 - Recibe la redirección del servidor OAuth2 con el código
    """
    try:
        code = request.args.get('code')
        encoded_state = request.args.get('state')
        
        if not code:
            _get_logger().warning("[OAUTH_CALLBACK_REDIRECT] Código faltante")
            return "Código faltante", 400
        
        # Decodificar el state desde base64url
        code_verifier = None
        original_state = None
        
        if encoded_state:
            try:
                # Convertir base64url a base64 estándar
                padded_state = encoded_state.replace('-', '+').replace('_', '/')
                padding = 4 - len(padded_state) % 4
                if padding != 4:
                    padded_state += '=' * padding
                
                # Decodificar
                state_data = json.loads(base64.b64decode(padded_state).decode('utf-8'))
                original_state = state_data.get('s')
                code_verifier = state_data.get('v')
                _get_logger().info("[OAUTH_CALLBACK_REDIRECT] Code verifier extraído del state codificado")
            except Exception as e:
                _get_logger().warning(f"[OAUTH_CALLBACK_REDIRECT] Error decodificando state: {e}")
        
        if not code_verifier:
            _get_logger().warning("[OAUTH_CALLBACK_REDIRECT] Code verifier faltante")
            return "Code verifier faltante. Inicia sesión desde el formulario de login.", 400
        
        _get_logger().info(f"[OAUTH_CALLBACK_REDIRECT] Intercambiando código por token con verifier: {code_verifier[:20]}...")
        
        # Obtener servicio OAuth
        oauth_service = get_oauth_service()
        
        if not oauth_service:
            _get_logger().error("[OAUTH_CALLBACK_REDIRECT] Servicio OAuth no disponible")
            return "Servicio OAuth no disponible", 500
        
        # Intercambiar código por token
        success, token_data = oauth_service.exchange_code_for_token(code, code_verifier)
        
        if not success:
            _get_logger().error(f"[OAUTH_CALLBACK_REDIRECT] Error intercambiando código: {token_data}")
            return f"Error intercambiando código: {token_data.get('error', 'Error desconocido')}", 400
        
        # Obtener información del usuario
        access_token = token_data.get('access_token')
        user_info = oauth_service.get_userinfo(access_token)
        
        # Guardar en sesión
        session['logged_in'] = True
        session['user_id'] = user_info.get('sub', 1) if user_info else 1
        session['email'] = user_info.get('email', '') if user_info else ''
        session['username'] = user_info.get('preferred_username', user_info.get('name', 'user')) if user_info else 'user'
        session['user_role'] = 'admin'
        session['oauth_token'] = access_token
        session['oauth_refresh_token'] = token_data.get('refresh_token')
        
        # Limpiar state y verifier de sesión
        session.pop('oauth_state', None)
        session.pop('oauth_code_verifier', None)
        
        _get_logger().info(f"[OAUTH_CALLBACK_REDIRECT] Login OAuth2 exitoso para: {session.get('username')}")
        
        # Redirigir a la página principal
        return redirect(url_for('main_page.index'))
        
    except Exception as e:
        _get_logger().error(f"[OAUTH_CALLBACK_REDIRECT] Error: {str(e)}")
        return f"Error: {str(e)}", 500


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout_page():
    """Página de logout"""
    # Intentar revocar token
    try:
        oauth_token = session.get('oauth_token')
        if oauth_token:
            oauth_service = get_oauth_service()
            if oauth_service:
                oauth_service.revoke_token(oauth_token)
    except:
        pass
    
    _get_logger().info("[LOGOUT] Usuario cerró sesión")
    session.clear()
    return redirect(url_for('auth.login_page'))