"""
Rutas de Proxy - Proxy de imágenes
"""
from flask import Blueprint, request, redirect
import requests
from urllib.parse import unquote

proxy_bp = Blueprint('proxy', __name__, url_prefix='/proxy-image')


def init_proxy_routes():
    """Inicializa las rutas de proxy"""
    pass


@proxy_bp.route('')
def proxy_image():
    """Proxy de imágenes"""
    url = request.args.get('url')
    if not url:
        return 'Missing url parameter', 400
    
    try:
        # Redireccionar a la URL original
        return redirect(unquote(url))
    except Exception as e:
        return f'Error: {str(e)}', 500
