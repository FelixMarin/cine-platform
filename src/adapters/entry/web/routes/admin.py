"""
Rutas de Administración
"""
from flask import Blueprint, render_template, jsonify
from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Blueprint para la página HTML del admin (sin prefijo /api)
admin_page_bp = Blueprint('admin_page', __name__)


@admin_page_bp.route('/admin/manage')
@admin_page_bp.route('/admin')
@require_auth
@require_role('admin')
def admin_page():
    """Página del panel de administración"""
    return render_template('pages/admin/dashboard.html')


def init_admin_routes():
    """Inicializa las rutas de admin"""
    pass


@admin_bp.route('/')
@require_auth
@require_role('admin')
def index():
    """Panel de administración"""
    return render_template('pages/admin/dashboard.html')


@admin_bp.route('/stats')
@require_auth
@require_role('admin')
def stats():
    """Estadísticas del sistema"""
    # Por ahora retornar stats vacíos
    return jsonify({
        'total_movies': 0,
        'total_series': 0,
        'storage_used': 0,
        'users': 0
    })


@admin_bp.route('/status')
@require_auth
def status():
    """Estado del sistema"""
    return jsonify({
        'status': 'running',
        'version': '1.0.0'
    })
