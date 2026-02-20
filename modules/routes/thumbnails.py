# modules/routes/thumbnails.py
"""
Blueprint de thumbnails: /thumbnails, /thumbnails/detect
"""
import os
from flask import Blueprint, session, jsonify, send_from_directory, make_response, request
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

thumbnails_bp = Blueprint('thumbnails', __name__)

# Servicio inyectado desde fuera
media_service = None


def init_media_service(service):
    """Inicializa el servicio de medios"""
    global media_service
    media_service = service


def is_logged_in():
    return session.get("logged_in") is True


@thumbnails_bp.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Sirve miniaturas de videos"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    # Validar filename para evitar path traversal
    if not media_service.is_path_safe(filename):
        logger.warning(f"Intento de path traversal en thumbnails: {filename}")
        return "Nombre de archivo inválido", 400
    
    thumbnails_folder = media_service.get_thumbnails_folder()
    accept_webp = 'image/webp' in request.headers.get('Accept', '')
    
    if filename.endswith('.jpg') and accept_webp:
        webp_filename = filename.replace('.jpg', '.webp')
        webp_path = os.path.join(thumbnails_folder, webp_filename)
        
        if os.path.exists(webp_path):
            response = make_response(send_from_directory(thumbnails_folder, webp_filename))
            response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
            response.headers['X-Image-Format'] = 'webp'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
    
    response = make_response(send_from_directory(thumbnails_folder, filename))
    response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
    response.headers['X-Image-Format'] = 'jpg' if filename.endswith('.jpg') else 'webp'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response


@thumbnails_bp.route('/thumbnails/detect/<filename>')
def detect_thumbnail_format(filename):
    """Detecta qué formatos de miniatura existen"""
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    
    # Validar filename
    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Intento de path traversal en detect: {filename}")
        return jsonify({"error": "Nombre de archivo inválido"}), 400
    
    thumbnails_folder = media_service.get_thumbnails_folder()
    base_name = os.path.splitext(filename)[0]
    
    jpg_path = os.path.join(thumbnails_folder, f"{base_name}.jpg")
    webp_path = os.path.join(thumbnails_folder, f"{base_name}.webp")
    
    return jsonify({
        "base_name": base_name,
        "has_jpg": os.path.exists(jpg_path),
        "has_webp": os.path.exists(webp_path),
        "jpg_url": f"/thumbnails/{base_name}.jpg" if os.path.exists(jpg_path) else None,
        "webp_url": f"/thumbnails/{base_name}.webp" if os.path.exists(webp_path) else None
    })
