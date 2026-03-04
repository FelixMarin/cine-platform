"""
Adaptador de entrada - Rutas de autenticación
Blueprint para /api/auth y login
"""
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for
import os
import base64
import json
import secrets
import hashlib

from src.core.use_cases.auth import LoginUseCase, LogoutUseCase
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.config.dependencies import get_oauth_service, get_auth_service

from src.infrastructure.logging import setup_logging
logger = setup_logging(os.environ.get("LOG_FOLDER"))

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
            
            # Extraer roles del token JWT si están disponibles
            roles = user_data.get('roles', [])
            if 'ROLE_ADMIN' in roles:
                user_role = 'admin'
            elif 'ROLE_USER' in roles:
                user_role = 'user'
            else:
                user_role = user_data.get('role', 'user')  # Por defecto 'user', nunca 'admin'
            
            session['user_role'] = user_role
            session['user_roles'] = roles  # Guardar lista completa de roles
            
            logger.info(f"[API LOGIN] Login exitoso para: {email}, rol: {user_role}")
            
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

@auth_bp.route('/api/auth/oauth2/start', methods=['POST'])
def start_oauth2_flow():
    """
    Inicia el flujo OAuth2. Genera code_verifier, guarda en sesión y devuelve la URL de autorización.
    El frontend debe redirigir a esta URL.
    """
    try:
        # Verificar que no hay sesión activa (para evitar accesos no autorizados)
        logger.info(f"[OAUTH_START] Request cookies: {dict(request.cookies)}")
        logger.info(f"[OAUTH_START] Session keys: {list(session.keys()) if session else 'No session'}")
        logger.info(f"[OAUTH_START] Is logged in: {is_logged_in()}")
        
        # Si ya hay una sesión activa, no permitir iniciar OAuth2
        if is_logged_in():
            logger.warning(f"[OAUTH_START] Usuario ya logueado, redirigiendo a página principal")
            return jsonify({
                'success': False,
                'error': 'Ya hay una sesión activa',
                'redirect': '/'
            })
        
        # Generar code_verifier y code_challenge
        code_verifier = _generate_code_verifier()
        code_challenge = _generate_code_challenge(code_verifier)
        
        # Limpiar cualquier code_verifier anterior y guardar el nuevo
        session.pop('oauth_code_verifier', None)
        session.pop('oauth_state', None)
        session['oauth_code_verifier'] = code_verifier
        
        # Generar state aleatorio
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        
        # Obtener configuración
        oauth2_url = os.environ.get('PUBLIC_OAUTH2_URL', 'http://localhost:8080').rstrip('/')
        client_id = os.environ.get('OAUTH2_CLIENT_ID', 'default-user')
        redirect_uri = os.environ.get('PUBLIC_REDIRECT_URI', 'http://localhost:5000/oauth/callback').rstrip('/')
        
        # Construir URL de autorización
        # NOTA: prompt=login fuerza al servidor OAuth2 a mostrar la pantalla de login
        # Esto asegura que el usuario tenga que introducir credenciales incluso si tiene
        # una sesión activa en el servidor OAuth2
        from urllib.parse import urlencode
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'openid profile read write',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state,
            'prompt': 'login',  # Forzar login screen en OAuth2 server
        }
        
        auth_url = f"{oauth2_url}/oauth2/authorize?{urlencode(params)}"
        logger.info(f"[OAUTH_START] URL de autorización generada: {auth_url[:100]}...")
        
        return jsonify({
            'success': True,
            'authorization_url': auth_url
        })
        
    except Exception as e:
        logger.error(f"[OAUTH_START] Error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    """Página de login"""
    # Verificar si hay parámetros OAuth2 en la query string (el usuario vino del flujo OAuth2)
    code_challenge = request.args.get('code_challenge')
    oauth_state = request.args.get('state')
    
    if request.method == 'GET':
        logger.info(f"[LOGIN_PAGE] GET request, is_logged_in: {is_logged_in()}, session keys: {list(session.keys())}")
        
        if is_logged_in():
            # Si ya está logueado y hay parámetros OAuth2, completar el flujo
            if code_challenge:
                # Regenerar verifier desde la sesión o generar nuevo
                return _complete_oauth_flow(code_challenge, oauth_state)
            logger.info("[LOGIN_PAGE] User is logged in, redirecting to main page")
            return redirect(url_for('main_page.index'))

        # Usar variables directamente, sin base64
        oauth2_url = os.environ.get('PUBLIC_OAUTH2_URL', 'http://localhost:8080').rstrip('/')
        client_id = os.environ.get('OAUTH2_CLIENT_ID', 'default-user')
        client_secret = os.environ.get('OAUTH2_CLIENT_SECRET', 'default-user-secret')
        redirect_uri = os.environ.get('PUBLIC_REDIRECT_URI', 'http://localhost:5000/oauth/callback').rstrip('/')

        logger.info(f"PUBLIC_OAUTH2_URL: {oauth2_url}")
        logger.info(f"OAUTH2_CLIENT_ID: {client_id}")
        logger.info(f"PUBLIC_REDIRECT_URI: {redirect_uri}")

        return render_template('login.html',
                              oauth2_url=oauth2_url,
                              client_id=client_id,
                              client_secret=client_secret,
                              redirect_uri=redirect_uri)

    # POST - Procesar login
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Obtener parámetros OAuth2 del form (si existen)
        code_challenge = request.form.get('code_challenge')
        oauth_state = request.form.get('state')

        if not email or not password:
            return render_template('login.html', error='Email y contraseña requeridos')

        logger.info(f"[LOGIN] Intento de login para usuario: {email}")

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
                    
                    # Extraer roles del token JWT si están disponibles
                    roles = user_data.get('roles', [])
                    if 'ROLE_ADMIN' in roles:
                        user_role = 'admin'
                    elif 'ROLE_USER' in roles:
                        user_role = 'user'
                    else:
                        user_role = user_data.get('role', 'user')  # Por defecto 'user', nunca 'admin'
                    
                    session['user_role'] = user_role
                    session['user_roles'] = roles  # Guardar lista completa de roles
                    session['oauth_token'] = oauth_service.token
                    logger.info(f"[LOGIN] OAuth exitoso para: {email}, rol: {user_role}")
                    
                    # Si hay code_challenge, completar el flujo OAuth2
                    if code_challenge:
                        return _complete_oauth_flow(code_challenge, oauth_state)
                    
                    return redirect(url_for('main_page.index'))
                # OAuth2 falló, intentar fallback
            except Exception as oauth_error:
                logger.warning(f"[LOGIN] OAuth falló: {oauth_error}")
                # OAuth2 no disponible, usar fallback
                pass

        # Fallback a credenciales locales (útil para desarrollo)
        valid_user = os.environ.get('APP_USER', 'default-user')
        valid_pass = os.environ.get('APP_PASSWORD', 'default-user-password')

        logger.info(f"[LOGIN] Verificando credenciales locales: {email} == {valid_user}")
        
        if email == valid_user and password == valid_pass:
            session['logged_in'] = True
            session['user_id'] = 1
            session['email'] = email
            session['username'] = email
            # En desarrollo local, por defecto es admin (solo para desarrollo)
            session['user_role'] = 'admin'
            session['user_roles'] = ['ROLE_ADMIN', 'ROLE_USER']
            logger.info(f"[LOGIN] Login exitoso para: {email} (modo desarrollo)")
            
            # Si hay code_challenge, completar el flujo OAuth2
            if code_challenge:
                return _complete_oauth_flow(code_challenge, oauth_state)
            
            return redirect(url_for('main_page.index'))
        else:
            logger.warning(f"[LOGIN] Credenciales incorrectas para: {email}")
            return render_template('login.html', error='Credenciales incorrectas')
            
    except Exception as e:
        logger.error(f"[LOGIN] Error: {e}")
        return render_template('login.html', error=f'Error: {str(e)}')


def _generate_code_verifier() -> str:
    """Genera un code_verifier aleatorio (43-128 caracteres)"""
    random_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    return verifier


def _generate_code_challenge(verifier: str) -> str:
    """Genera un code_challenge a partir del code_verifier usando SHA-256"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    return challenge


def _complete_oauth_flow(code_challenge: str, state: str = None):
    """
    Completa el flujo OAuth2 después del login.
    Genera el code_verifier, lo guarda en sesión y redirige al servidor OAuth2.
    """
    try:
        logger.info(f"[OAUTH_FLOW] Iniciando flujo OAuth2 con code_challenge: {code_challenge[:30]}...")
        
        # Generar code_verifier
        code_verifier = _generate_code_verifier()
        logger.info(f"[OAUTH_FLOW] Code verifier generado: {code_verifier[:30]}...")
        
        # Guardar en sesión para usarlo después en el callback
        session['oauth_code_verifier'] = code_verifier
        logger.info(f"[OAUTH_FLOW] Code verifier guardado en sesión")
        
        # Obtener configuración
        oauth2_url = os.environ.get('PUBLIC_OAUTH2_URL', 'http://localhost:8080').rstrip('/')
        client_id = os.environ.get('OAUTH2_CLIENT_ID', 'cine-platform')
        redirect_uri = os.environ.get('PUBLIC_REDIRECT_URI', 'http://localhost:5000/oauth/callback').rstrip('/')
        
        # Construir URL de autorización
        # prompt=login fuerza al servidor OAuth2 a mostrar la pantalla de login
        from urllib.parse import urlencode
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'openid profile read write',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'login',  # Forzar login screen
        }
        if state:
            params['state'] = state
        
        auth_url = f"{oauth2_url}/oauth2/authorize?{urlencode(params)}"
        logger.info(f"[OAUTH_FLOW] Redirigiendo a: {auth_url}")
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"[OAUTH_FLOW] Error: {e}")
        return render_template('login.html', error=f'Error al completar OAuth: {str(e)}')


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
            logger.warning("[OAUTH_CALLBACK] Código o verifier faltante")
            return jsonify({'success': False, 'error': 'Código o verifier faltante'}), 400

        logger.info("[OAUTH_CALLBACK] Intercambiando código por token")

        # Obtener servicio OAuth
        oauth_service = get_oauth_service()

        if not oauth_service:
            logger.error("[OAUTH_CALLBACK] Servicio OAuth no disponible")
            return jsonify({'success': False, 'error': 'Servicio OAuth no disponible'}), 500

        # Intercambiar código por token
        success, token_data = oauth_service.exchange_code_for_token(code, code_verifier)

        if not success:
            logger.error(f"[OAUTH_CALLBACK] Error intercambiando código: {token_data}")
            return jsonify({'success': False, 'error': token_data.get('error', 'Error desconocido')}), 400

        # Obtener información del usuario
        access_token = token_data.get('access_token')
        user_info = oauth_service.get_userinfo(access_token)

        # Guardar en sesión
        session['logged_in'] = True
        session['user_id'] = user_info.get('sub', 1) if user_info else 1
        session['email'] = user_info.get('email', '') if user_info else ''
        session['username'] = user_info.get('preferred_username', user_info.get('name', 'user')) if user_info else 'user'
        
        # Extraer roles del token JWT - determinar rol del usuario
        roles = user_info.get('roles', []) if user_info else []
        
        if 'ROLE_ADMIN' in roles:
            user_role = 'admin'
        elif 'ROLE_USER' in roles:
            user_role = 'user'
        else:
            user_role = 'user'  # Por defecto 'user', nunca 'admin'
        
        session['user_role'] = user_role
        session['user_roles'] = roles  # Guardar lista completa de roles
        
        session['oauth_token'] = access_token
        session['oauth_refresh_token'] = token_data.get('refresh_token')
        session['oauth_expires_at'] = token_data.get('expires_at')

        logger.info(f"[OAUTH_CALLBACK] Login OAuth2 exitoso para: {session.get('username')}, rol: {user_role}")

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK] Error: {e}")
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
            logger.warning("[OAUTH_CALLBACK_REDIRECT] Código faltante")
            return "Código faltante", 400
        
        # Decodificar el state desde base64url o obtener desde sesión
        code_verifier = None
        original_state = None
        
        # Primero intentar obtener desde la sesión (nuevo flujo)
        code_verifier = session.get('oauth_code_verifier')
        logger.info(f"[OAUTH_CALLBACK_REDIRECT] Sesión keys: {list(session.keys())}")
        logger.info(f"[OAUTH_CALLBACK_REDIRECT] Code verifier en sesión: {bool(code_verifier)}")
        if code_verifier:
            logger.info(f"[OAUTH_CALLBACK_REDIRECT] Code verifier obtenido de la sesión: {code_verifier[:20]}...")
        elif encoded_state:
            # Fallback: intentar decodificar desde state (flujo antiguo)
            logger.info(f"[OAUTH_CALLBACK_REDIRECT] Intentando decodificar state: {encoded_state}")
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
                logger.info("[OAUTH_CALLBACK_REDIRECT] Code verifier extraído del state codificado")
            except Exception as e:
                logger.warning(f"[OAUTH_CALLBACK_REDIRECT] Error decodificando state: {e}")
        
        if not code_verifier:
            logger.warning("[OAUTH_CALLBACK_REDIRECT] Code verifier faltante")
            return "Code verifier faltante. Inicia sesión desde el formulario de login.", 400
        
        logger.info(f"[OAUTH_CALLBACK_REDIRECT] Intercambiando código por token con verifier: {code_verifier[:20]}...")
        
        # Obtener servicio OAuth
        oauth_service = get_oauth_service()
        
        if not oauth_service:
            logger.error("[OAUTH_CALLBACK_REDIRECT] Servicio OAuth no disponible")
            return "Servicio OAuth no disponible", 500
        
        # Intercambiar código por token
        success, token_data = oauth_service.exchange_code_for_token(code, code_verifier)
        
        if not success:
            logger.error(f"[OAUTH_CALLBACK_REDIRECT] Error intercambiando código: {token_data}")
            return f"Error intercambiando código: {token_data.get('error', 'Error desconocido')}", 400
        
        # Obtener información del usuario
        access_token = token_data.get('access_token')
        user_info = oauth_service.get_userinfo(access_token)
        
        # Guardar en sesión
        session['logged_in'] = True
        session['user_id'] = user_info.get('sub', 1) if user_info else 1
        session['email'] = user_info.get('email', '') if user_info else ''
        session['username'] = user_info.get('preferred_username', user_info.get('name', 'user')) if user_info else 'user'
        
        # Extraer roles del token JWT - determinar rol del usuario
        roles = user_info.get('roles', []) if user_info else []
        
        if 'ROLE_ADMIN' in roles:
            user_role = 'admin'
        elif 'ROLE_USER' in roles:
            user_role = 'user'
        else:
            user_role = 'user'  # Por defecto 'user', nunca 'admin'
        
        session['user_role'] = user_role
        session['user_roles'] = roles  # Guardar lista completa de roles
        
        session['oauth_token'] = access_token
        session['oauth_refresh_token'] = token_data.get('refresh_token')
        
        # Limpiar state y verifier de sesión
        session.pop('oauth_state', None)
        session.pop('oauth_code_verifier', None)
        
        logger.info(f"[OAUTH_CALLBACK_REDIRECT] Login OAuth2 exitoso para: {session.get('username')}, rol: {user_role}")
        
        # Redirigir a la página principal
        return redirect(url_for('main_page.index'))
        
    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK_REDIRECT] Error: {str(e)}")
        return f"Error: {str(e)}", 500


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout_page():
    """Página de logout"""
    from flask import current_app, make_response
    
    # Ver cookies recibidas
    logger.info(f"[LOGOUT] Cookies recibidas: {dict(request.cookies)}")
    
    # Intentar revocar token en el servidor OAuth2
    try:
        oauth_token = session.get('oauth_token')
        if oauth_token:
            oauth_service = get_oauth_service()
            if oauth_service:
                oauth_service.revoke_token(oauth_token)
                logger.info("[LOGOUT] Token revocado en servidor OAuth2")
    except Exception as e:
        logger.warning(f"[LOGOUT] Error revocando token: {e}")
    
    logger.info("[LOGOUT] Usuario cerró sesión - limpiando datos")
    
    # Limpiar TODOS los datos de sesión
    session_keys = list(session.keys())
    logger.info(f"[LOGOUT] Keys en sesión antes de limpiar: {session_keys}")
    session.clear()
    
    # Forzar la modificación de la sesión para que se guarde
    session.modified = True
    
    # Crear respuesta de redirección
    response = make_response(redirect(url_for('auth.login_page')))
    
    # Opciones de cookie base
    base_options = {
        'httponly': True,
        'samesite': 'Lax',
    }
    
    # Añadir secure si está configurado
    if current_app.config.get('SESSION_COOKIE_SECURE', False):
        base_options['secure'] = True
    
    # 1. Sin dominio (cookie por defecto)
    response.set_cookie('session', '', max_age=0, path='/', **base_options)
    
    # 2. Con el dominio configurado
    try:
        cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')
        cookie_path = current_app.config.get('SESSION_COOKIE_PATH', '/')
        logger.info(f"[LOGOUT] Cookie domain: {cookie_domain}, path: {cookie_path}")
        if cookie_domain:
            # Usar solo el dominio, NO path de nuevo (evitar error "multiple values for keyword argument 'path'")
            response.set_cookie('session', '', max_age=0, domain=cookie_domain, **base_options)
    except Exception as e:
        logger.warning(f"[LOGOUT] Error eliminando cookie de dominio: {e}")
    
    logger.info("[LOGOUT] Session cleared, all cookies set to expire, redirecting to login")
    return response


# ============================
# RUTAS DE LOGOUT
# ============================

@auth_bp.route('/logout-check', methods=['GET'])
def logout_check():
    """Endpoint para verificar el estado del logout"""
    logger.info(f"[LOGOUT_CHECK] Cookies: {dict(request.cookies)}")
    logger.info(f"[LOGOUT_CHECK] Session keys: {list(session.keys())}")
    logger.info(f"[LOGOUT_CHECK] Is logged in: {is_logged_in()}")
    return jsonify({
        'logged_in': is_logged_in(),
        'session_keys': list(session.keys()),
        'cookies': list(request.cookies.keys())
    })