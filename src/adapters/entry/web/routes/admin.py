"""
Rutas de Administración
"""
from flask import Blueprint, render_template, jsonify

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Blueprint para la página HTML del admin (sin prefijo /api)
admin_page_bp = Blueprint('admin_page', __name__)


@admin_page_bp.route('/admin/manage')
@admin_page_bp.route('/admin')
def admin_page():
    """Página del panel de administración"""
    return render_template('admin_panel.html')


def init_admin_routes():
    """Inicializa las rutas de admin"""
    pass


@admin_bp.route('/')
def index():
    """Panel de administración"""
    return render_template('admin_panel.html')


@admin_bp.route('/stats')
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
def status():
    """Estado del sistema"""
    return jsonify({
        'status': 'running',
        'version': '1.0.0'
    })
