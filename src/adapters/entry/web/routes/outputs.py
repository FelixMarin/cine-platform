"""
Rutas de Outputs - Archivos de salida
"""
from flask import Blueprint, send_from_directory, jsonify, redirect, url_for, session
from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role
import os

outputs_bp = Blueprint('outputs', __name__, url_prefix='/outputs')


def init_outputs_routes():
    """Inicializa las rutas de outputs"""
    pass


@outputs_bp.route('/<path:filename>')
@require_role('admin')
def download_file(filename):
    """Descarga archivo de salida - solo admins"""
    output_folder = os.environ.get('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    return send_from_directory(output_folder, filename)


# Ruta adicional /download que redirige a /outputs/ para compatibilidad
download_bp = Blueprint('download', __name__)

@download_bp.route('/download/<path:filename>')
@require_role('admin')
def download_redirect(filename):
    """Ruta de descarga - solo admins"""
    return redirect(url_for('outputs.download_file', filename=filename))


@outputs_bp.route('/list')
def list_outputs():
    """Lista archivos de salida"""
    output_folder = os.environ.get('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    files = []
    if os.path.exists(output_folder):
        files = [f for f in os.listdir(output_folder) if os.path.isfile(os.path.join(output_folder, f))]
    return jsonify({'files': files})
