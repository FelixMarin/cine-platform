# modules/routes/outputs.py
"""
Blueprint de outputs: /outputs, /download
"""
import os
import logging
from flask import Blueprint, session, send_from_directory

logger = logging.getLogger(__name__)

outputs_bp = Blueprint('outputs', __name__)

# Servicios inyectados desde fuera
optimizer_service = None
media_service = None


def init_services(optimizer_svc, media_svc):
    """Inicializa los servicios"""
    global optimizer_service, media_service
    optimizer_service = optimizer_svc
    media_service = media_svc


# Asignar como método del blueprint para permitir llamada directa
outputs_bp.init_services = staticmethod(init_services)


def is_logged_in():
    return session.get("logged_in") is True


@outputs_bp.route('/outputs/<filename>')
def serve_output(filename):
    """Sirve archivos de salida optimizados"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    # Validar filename
    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Intento de path traversal en outputs: {filename}")
        return "Nombre de archivo inválido", 400
        
    return send_from_directory(optimizer_service.get_output_folder(), filename)


@outputs_bp.route('/download/<path:filename>')
def download_file(filename):
    """Descarga archivos"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    if not media_service:
        return "Servicio no disponible", 500
    
    file_path = media_service.get_safe_path(filename)
    if not file_path:
        logger.warning(f"Intento de descarga no autorizada: {filename}")
        return "Archivo no encontrado", 404
    
    response = send_from_directory(
        os.path.dirname(file_path), 
        os.path.basename(file_path), 
        as_attachment=True
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
