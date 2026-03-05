"""
Middleware de autenticación para Flask
Protege las rutas que requieren autenticación
"""
import logging
from functools import wraps
from flask import session, redirect, url_for, jsonify, request

# Logger para este módulo
logger = logging.getLogger(__name__)


def require_auth(f):
    """
    Decorador que requiere autenticación para acceder a una ruta.
    Si el usuario no está autenticado, redirige a la página de login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # === LOGS DE DEPURACIÓN ===
        logger.info(f"[AUTH_MIDDLEWARE] require_auth - Path: {request.path}")
        logger.info(f"[AUTH_MIDDLEWARE] session keys: {list(session.keys())}")
        logger.info(f"[AUTH_MIDDLEWARE] logged_in: {session.get('logged_in', False)}")
        logger.info(f"[AUTH_MIDDLEWARE] user_role: {session.get('user_role', 'NOT_SET')}")
        logger.info(f"[AUTH_MIDDLEWARE] user_id: {session.get('user_id', 'NOT_SET')}")
        # ===========================
        
        if not session.get('logged_in', False):
            # Si es una solicitud AJAX/API, devolver 401
            if request.is_json or request.path.startswith('/api/'):
                logger.warning(f"[AUTH_MIDDLEWARE] AUTH_REQUIRED - Path: {request.path}")
                return jsonify({'error': 'Autenticación requerida', 'code': 'AUTH_REQUIRED'}), 401
            # Si es una página web, redirigir al login
            logger.warning(f"[AUTH_MIDDLEWARE] Redirecting to login - Path: {request.path}")
            return redirect(url_for('auth.login_page'))
        
        logger.info(f"[AUTH_MIDDLEWARE] Access granted - Path: {request.path}, Role: {session.get('user_role')}")
        return f(*args, **kwargs)
    return decorated_function


def require_role(*roles):
    """
    Decorador que requiere un rol específico para acceder a una ruta.
    
    Args:
        roles: Roles permitidos (ej: 'admin', 'user')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # === LOGS DE DEPURACIÓN ===
            logger.info(f"[AUTH_MIDDLEWARE] require_role - Path: {request.path}, Required roles: {roles}")
            logger.info(f"[AUTH_MIDDLEWARE] session keys: {list(session.keys())}")
            logger.info(f"[AUTH_MIDDLEWARE] logged_in: {session.get('logged_in', False)}")
            logger.info(f"[AUTH_MIDDLEWARE] user_role: {session.get('user_role', 'NOT_SET')}")
            logger.info(f"[AUTH_MIDDLEWARE] user_roles (list): {session.get('user_roles', [])}")
            # ===========================
            
            if not session.get('logged_in', False):
                if request.is_json or request.path.startswith('/api/'):
                    logger.warning(f"[AUTH_MIDDLEWARE] AUTH_REQUIRED (require_role) - Path: {request.path}")
                    return jsonify({'error': 'Autenticación requerida', 'code': 'AUTH_REQUIRED'}), 401
                return redirect(url_for('auth.login_page'))
            
            user_role = session.get('user_role', '')
            logger.info(f"[AUTH_MIDDLEWARE] Checking role - user_role: '{user_role}', required: {roles}")
            
            if user_role not in roles:
                logger.warning(f"[AUTH_MIDDLEWARE] FORBIDDEN - user_role '{user_role}' not in {roles}")
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Permisos insuficientes', 'code': 'FORBIDDEN'}), 403
                return redirect(url_for('auth.login_page'))
            
            logger.info(f"[AUTH_MIDDLEWARE] Role OK - Access granted to {request.path}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_authenticated():
    """Verifica si el usuario actual está autenticado"""
    is_auth = session.get('logged_in', False)
    logger.info(f"[AUTH_MIDDLEWARE] is_authenticated: {is_auth}")
    return is_auth


def get_current_user():
    """Obtiene los datos del usuario actual autenticado"""
    if is_authenticated():
        user_data = {
            'id': session.get('user_id'),
            'email': session.get('email'),
            'username': session.get('username'),
            'role': session.get('user_role'),
            'roles': session.get('user_roles', [])  # Lista completa de roles del token
        }
        logger.info(f"[AUTH_MIDDLEWARE] get_current_user: {user_data}")
        return user_data
    logger.info("[AUTH_MIDDLEWARE] get_current_user: None (not authenticated)")
    return None
