"""
Adaptador de entrada - Rutas de autenticación
Blueprint para /api/auth y login
"""
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for

from src.core.use_cases.auth import LoginUseCase, LogoutUseCase

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
    
    if _login_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email y password son requeridos'}), 400
        
        success, user_data = _login_use_case.execute(email, password)
        
        if success:
            # Guardar en sesión
            session['logged_in'] = True
            session['user_id'] = user_data.get('id')
            session['email'] = user_data.get('email')
            session['username'] = user_data.get('username')
            
            return jsonify({
                'success': True,
                'user': user_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Credenciales inválidas'
            }), 401
    
    except Exception as e:
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
    
    if request.method == 'GET':
        if is_logged_in():
            return redirect(url_for('auth.index'))
        return render_template('login.html')
    
    # POST - Procesar login
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('login.html', error='Email y contraseña requeridos')
        
        # Intentar OAuth2 primero
        oauth_service = get_oauth_service()
        oauth_success = False
        
        if oauth_service:
            try:
                success, user_data = oauth_service.login(email, password)
                if success:
                    session['logged_in'] = True
                    session['user_id'] = 1
                    session['user_email'] = user_data.get('username', email)
                    session['user_role'] = 'admin'
                    session['oauth_token'] = oauth_service.token
                    return redirect(url_for('auth.index'))
                # OAuth2 falló, intentar fallback
            except Exception as oauth_error:
                # OAuth2 no disponible, usar fallback
                pass
        
        # Fallback a credenciales locales (útil para desarrollo)
        valid_user = os.environ.get('APP_USER', 'admin')
        valid_pass = os.environ.get('APP_PASSWORD', 'Admin1')
        
        if email == valid_user and password == valid_pass:
            session['logged_in'] = True
            session['user_id'] = 1
            session['user_email'] = email
            session['user_role'] = 'admin'
            return redirect(url_for('auth.root'))
        else:
            return render_template('login.html', error='Credenciales incorrectas')
            
    except Exception as e:
        return render_template('login.html', error=f'Error: {str(e)}')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout_page():
    """Página de logout"""
    session.clear()
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/')
def root():
    """Página principal"""
    return render_template('index.html')


@auth_bp.route('/index')
def index():
    """Página principal alternativa"""
    return render_template('index.html')
