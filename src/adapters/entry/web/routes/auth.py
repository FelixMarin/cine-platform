"""
Adaptador de entrada - Rutas de autenticación
Blueprint para /api/auth y login
"""
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for

from src.core.use_cases.auth import LoginUseCase, LogoutUseCase
from src.adapters.entry.web.middleware.auth_middleware import require_auth

logger = None


def setup_logging(log_folder):
    """Setup de logging - se configurará después"""
    import logging
    global logger
    if logger is None:
        logger = logging.getLogger(__name__)
    return logger


auth_bp = Blueprint('auth', __name__)

# Blueprint para la página principal (sin prefijo)
main_page_bp = Blueprint('main_page', __name__)


@main_page_bp.route('/status')
def status():
    """Estado de la API"""
    from flask import jsonify
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
    import os
    # Get the static folder path - use current working directory
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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[API LOGIN] Intento de login - LoginUseCase: {_login_use_case}")
    
    if _login_use_case is None:
        logger.error("[API LOGIN] LoginUseCase no inicializado")
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email y password son requeridos'}), 400
        
        logger.info(f"[API LOGIN] Email: {email}")
        
        success, user_data = _login_use_case.execute(email, password)
        
        if success:
            # Guardar en sesión
            session['logged_in'] = True
            session['user_id'] = user_data.get('id')
            session['email'] = user_data.get('email')
            session['username'] = user_data.get('username')
            session['user_role'] = user_data.get('role', 'admin')
            
            logger.info(f"[API LOGIN] Login exitoso para: {email}")
            
            return jsonify({
                'success': True,
                'user': user_data
            })
        else:
            logger.warning(f"[API LOGIN] Credenciales incorrectas para: {email}")
            return jsonify({
                'success': False,
                'error': 'Credenciales inválidas'
            }), 401
    
    except Exception as e:
        logger.error(f"[API LOGIN] Error: {e}")
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
    """Página de login (GET) y procesamiento del login (POST)"""
    from src.adapters.config.dependencies import get_oauth_service
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'GET':
        if is_logged_in():
            return redirect(url_for('main_page.index'))
        return render_template('login.html')
    
    # POST - Procesar login
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('login.html', error='Email y contraseña requeridos')
        
        logger.info(f"[LOGIN] Intento de login para usuario: {email}")
        
        # Intentar OAuth2 primero
        oauth_service = get_oauth_service()
        oauth_success = False
        
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
                    logger.info(f"[LOGIN] OAuth exitoso para: {email}")
                    return redirect(url_for('main_page.index'))
                # OAuth2 falló, intentar fallback
            except Exception as oauth_error:
                logger.warning(f"[LOGIN] OAuth falló: {oauth_error}")
                # OAuth2 no disponible, usar fallback
                pass
        
        # Fallback a credenciales locales (útil para desarrollo)
        valid_user = os.environ.get('APP_USER', 'admin')
        valid_pass = os.environ.get('APP_PASSWORD', 'Admin1')
        
        logger.info(f"[LOGIN] Verificando credenciales locales: {email} == {valid_user}")
        
        if email == valid_user and password == valid_pass:
            session['logged_in'] = True
            session['user_id'] = 1
            session['email'] = email
            session['username'] = email
            session['user_role'] = 'admin'
            logger.info(f"[LOGIN] Login exitoso para: {email}")
            return redirect(url_for('main_page.index'))
        else:
            logger.warning(f"[LOGIN] Credenciales incorrectas para: {email}")
            return render_template('login.html', error='Credenciales incorrectas')
            
    except Exception as e:
        logger.error(f"[LOGIN] Error: {e}")
        return render_template('login.html', error=f'Error: {str(e)}')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout_page():
    """Página de logout"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[LOGOUT] Usuario cerró sesión")
    session.clear()
    return redirect(url_for('auth.login_page'))


# NOTA: Las rutas / e /index están definidas en main_page_bp con @require_auth
# Las rutas duplicadas aquí han sido eliminadas para evitar conflictos
