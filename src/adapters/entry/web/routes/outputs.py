"""
Rutas de Outputs - Archivos de salida
"""
from flask import Blueprint, send_from_directory, jsonify
import os

outputs_bp = Blueprint('outputs', __name__, url_prefix='/outputs')


def init_outputs_routes():
    """Inicializa las rutas de outputs"""
    pass


@outputs_bp.route('/<path:filename>')
def download_file(filename):
    """Descarga archivo de salida"""
    output_folder = os.environ.get('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    return send_from_directory(output_folder, filename)


@outputs_bp.route('/list')
def list_outputs():
    """Lista archivos de salida"""
    output_folder = os.environ.get('OUTPUT_FOLDER', '/tmp/cineplatform/outputs')
    files = []
    if os.path.exists(output_folder):
        files = [f for f in os.listdir(output_folder) if os.path.isfile(os.path.join(output_folder, f))]
    return jsonify({'files': files})
