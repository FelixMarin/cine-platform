"""
Rutas de Thumbnails - Miniaturas
"""
from flask import Blueprint, send_from_directory, jsonify, abort
import os

thumbnails_bp = Blueprint('thumbnails', __name__, url_prefix='/api/thumbnails')


def init_thumbnails_routes():
    """Inicializa las rutas de thumbnails"""
    pass


@thumbnails_bp.route('/<path:filename>')
def get_thumbnail(filename):
    """Obtiene una miniatura"""
    thumbnail_folder = os.environ.get('THUMBNAIL_FOLDER', '/tmp/cineplatform/thumbnails')
    
    # Buscar en la carpeta de thumbnails
    path = os.path.join(thumbnail_folder, filename)
    if os.path.exists(path):
        return send_from_directory(thumbnail_folder, filename)
    
    # Si no existe, retornar imagen por defecto
    return send_from_directory('static/images', 'default.jpg')


@thumbnails_bp.route('/list')
def list_thumbnails():
    """Lista miniaturas disponibles"""
    thumbnail_folder = os.environ.get('THUMBNAIL_FOLDER', '/tmp/cineplatform/thumbnails')
    files = []
    if os.path.exists(thumbnail_folder):
        files = [f for f in os.listdir(thumbnail_folder) if f.endswith(('.jpg', '.png', '.webp'))]
    return jsonify({'thumbnails': files})
