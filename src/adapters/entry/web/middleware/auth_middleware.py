"""
Middleware de autenticación para Flask
Protege las rutas que requieren autenticación
"""
import logging
from functools import wraps

from flask import jsonify, redirect, request, session

# Logger para este módulo
logger = logging.getLogger(__name__)


def require_auth(f):
    """
    Decorador que requiere autenticación para acceder a una ruta.
    Si el usuario no está autenticado, redirige a la página de login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Solo loggear si hay error de autenticación
        if request.path == '/login':
            return f(*args, **kwargs)

        if not session.get('logged_in', False):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Autenticación requerida', 'code': 'AUTH_REQUIRED'}), 401
            return redirect('/login')

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
            if not session.get('logged_in', False):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Autenticación requerida', 'code': 'AUTH_REQUIRED'}), 401
                return redirect('/login')

            user_role = session.get('user_role', '')

            if user_role not in roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Permisos insuficientes', 'code': 'FORBIDDEN'}), 403
                return redirect('/login')

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_authenticated():
    """Verifica si el usuario actual está autenticado"""
    return session.get('logged_in', False)


def get_current_user():
    """Obtiene los datos del usuario actual autenticado"""
    if is_authenticated():
        return {
            'id': session.get('user_id'),
            'email': session.get('email'),
            'username': session.get('username'),
            'role': session.get('user_role'),
            'roles': session.get('user_roles', [])
        }
    return None
