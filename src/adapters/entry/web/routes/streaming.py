"""
Rutas de Streaming - Reproducción de video
"""
from flask import Blueprint, send_file, request, Response, jsonify
import os
import mimetypes

streaming_bp = Blueprint('streaming', __name__, url_prefix='/api/streaming')

# Blueprint adicional para /stream/ (sin prefijo /api/)
stream_page_bp = Blueprint('stream_page', __name__)


@stream_page_bp.route('/stream/<path:filename>')
def stream_page_video(filename):
    """Stream de video en /stream/ (para compatibilidad con templates)"""
    return stream_video(filename)


def init_streaming_routes():
    """Inicializa las rutas de streaming"""
    pass


@streaming_bp.route('/<path:filename>')
def stream_video(filename):
    """Stream de video con soporte para Range requests"""
    # Obtener la ruta del archivo
    movies_folder = os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
    
    # URL decode el filename
    import urllib.parse
    filename = urllib.parse.unquote(filename)
    
    # El path de la URL no incluye el leading slash, pero las rutas son absolutas
    # Agregar '/' al inicio si no lo tiene
    if not filename.startswith('/'):
        filename = '/' + filename
    
    # Verificar si es una ruta válida existente
    # Primero probar como ruta absoluta
    if os.path.exists(filename):
        file_path = filename
    # Luego probar prependeando MOVIES_FOLDER
    elif os.path.exists(os.path.join(movies_folder, filename)):
        file_path = os.path.join(movies_folder, filename)
    else:
        return 'File not found', 404
    
    if not os.path.exists(file_path):
        return 'File not found', 404
    
    # Obtener tamaño del archivo
    file_size = os.path.getsize(file_path)
    
    # Obtener rango de bytes si existe
    range_header = request.headers.get('Range')
    
    if range_header:
        # Parsear rango
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Limitar el rango
        if end >= file_size:
            end = file_size - 1
        
        # Calcular tamaño del chunk
        chunk_size = end - start + 1
        
        # Leer el chunk
        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(chunk_size)
        
        # Headers de respuesta
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': chunk_size,
            'Content-Type': 'video/mp4',
        }
        
        return Response(data, status=206, headers=headers)
    else:
        # Enviar archivo completo
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=filename
        )


@streaming_bp.route('/info/<path:filename>')
def video_info(filename):
    """Información del video"""
    movies_folder = os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
    file_path = os.path.join(movies_folder, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    file_size = os.path.getsize(file_path)
    return jsonify({
        'filename': filename,
        'size': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2)
    })
