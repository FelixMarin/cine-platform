# modules/routes/proxy.py
"""
Proxy para imágenes de OMDb/IMDb
"""
import requests
import logging
from flask import Blueprint, request, send_file, abort
from io import BytesIO

logger = logging.getLogger(__name__)

proxy_bp = Blueprint('proxy', __name__)

@proxy_bp.route('/proxy-image')
def proxy_image():
    """Endpoint que sirve como proxy para imágenes externas"""
    url = request.args.get('url')
    if not url:
        return abort(400, "URL no proporcionada")
    
    try:
        # Hacer la petición desde el servidor (sin CORS)
        response = requests.get(url, timeout=10, stream=True)
        
        if response.status_code != 200:
            logger.warning(f"Error obteniendo imagen: {response.status_code}")
            return abort(404)
        
        # Devolver la imagen como archivo
        return send_file(
            BytesIO(response.content),
            mimetype=response.headers.get('Content-Type', 'image/jpeg')
        )
    except Exception as e:
        logger.error(f"Error en proxy de imagen: {e}")
        return abort(500)