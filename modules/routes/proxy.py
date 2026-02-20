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

# modules/routes/proxy.py

# modules/routes/proxy.py

@proxy_bp.route('/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url:
        return redirect(url_for('static', filename='images/default.jpg'))
    
    try:
        response = requests.get(url, timeout=10, stream=True)
        
        if response.status_code != 200:
            logger.warning(f"Imagen no encontrada (HTTP {response.status_code}): {url}")
            return redirect(url_for('static', filename='images/default.jpg'))
        
        return send_file(
            BytesIO(response.content),
            mimetype=response.headers.get('Content-Type', 'image/jpeg')
        )
    except Exception as e:
        logger.error(f"Error en proxy de imagen: {e}")
        return redirect(url_for('static', filename='images/default.jpg'))