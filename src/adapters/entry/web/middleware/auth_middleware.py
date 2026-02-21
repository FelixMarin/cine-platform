"""
Middleware de autenticación para Flask
Protege las rutas que requieren autenticación
"""
from functools import wraps
from flask import session, redirect, url_for, jsonify, request


def require_auth(f):
    """
    Decorador que requiere autenticación para acceder a una ruta.
    Si el usuario no está autenticado, redirige a la página de login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in', False):
            # Si es una solicitud AJAX/API, devolver 401
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Autenticación requerida', 'code': 'AUTH_REQUIRED'}), 401
            # Si es una página web, redirigir al login
            return redirect(url_for('auth.login_page'))
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
                return redirect(url_for('auth.login_page'))
            
            user_role = session.get('user_role', '')
            if user_role not in roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Permisos insuficientes', 'code': 'FORBIDDEN'}), 403
                return redirect(url_for('auth.index'))
            
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
            'role': session.get('user_role')
        }
    return None
