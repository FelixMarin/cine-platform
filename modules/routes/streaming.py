# modules/routes/streaming.py
"""
Blueprint de streaming: /, /play, /stream
"""
import os
import re
import logging
from flask import Blueprint, render_template, request, session, Response

logger = logging.getLogger(__name__)

streaming_bp = Blueprint('streaming', __name__)

# Servicio inyectado desde fuera
media_service = None


def init_media_service(service):
    """Inicializa el servicio de medios"""
    global media_service
    media_service = service


def is_logged_in():
    return session.get("logged_in") is True


def clean_filename(filename):
    """Limpia el nombre del archivo para mostrar"""
    name = re.sub(r'[-_]?optimized', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'\.(mkv|mp4|avi|mov)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[._-]', ' ', name)
    return ' '.join(word.capitalize() for word in name.split())


@streaming_bp.route('/')
def index():
    """Página principal con lista de contenido"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    movies, series = media_service.list_content()
    return render_template("index.html", movies=movies, series=series)


@streaming_bp.route('/play/<path:filename>')
def play(filename):
    """Página de reproducción de video"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    # Validación robusta de path traversal
    if not media_service.is_path_safe(filename):
        logger.warning(f"Intento de path traversal en play: {repr(filename)}")
        return "Nombre de archivo inválido", 400
    
    # Verificar que el archivo existe
    file_path = media_service.get_safe_path(filename)
    if not file_path:
        return "Archivo no encontrado", 404
    
    base_name = os.path.basename(filename)
    display_name = clean_filename(base_name)
    
    return render_template("play.html", filename=filename, sanitized_name=display_name)


@streaming_bp.route('/stream/<path:filename>')
def stream_video(filename):
    """Endpoint de streaming de video con soporte Range"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    file_path = media_service.get_safe_path(filename)
    if not file_path or not os.path.exists(file_path):
        logger.warning(f"Archivo no encontrado o acceso no autorizado: {filename}")
        return "Archivo no encontrado", 404

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)

    if range_header:
        try:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            
            if start < 0 or end >= file_size or start > end:
                return "Rango inválido", 416
        except (ValueError, IndexError):
            return "Rango inválido", 416
    else:
        start = 0
        end = file_size - 1

    length = end - start + 1

    def generate():
        try:
            with open(file_path, "rb") as video:
                video.seek(start)
                bytes_remaining = length
                chunk_size = 1024 * 1024  # 1MB
                
                while bytes_remaining > 0:
                    chunk = video.read(min(chunk_size, bytes_remaining))
                    if not chunk:
                        break
                    yield chunk
                    bytes_remaining -= len(chunk)
        except Exception as e:
            logger.error(f"Error en streaming: {e}")

    content_type = "video/mp4" if filename.endswith(".mp4") else "video/x-matroska"

    response = Response(generate(), status=206, content_type=content_type)
    response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    response.headers.add("X-Content-Type-Options", "nosniff")
    return response
