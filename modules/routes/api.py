# modules/routes/api.py
"""
Blueprint de API: /api/movies, /api/thumbnail-status
"""
import unicodedata
import time
import logging
from flask import Blueprint, session, jsonify, request

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# Servicio inyectado desde fuera
media_service = None


def init_media_service(service):
    """Inicializa el servicio de medios"""
    global media_service
    media_service = service


def is_logged_in():
    return session.get("logged_in") is True


def normalize_dict(d):
    """Normaliza caracteres Unicode en diccionarios"""
    if isinstance(d, dict):
        return {unicodedata.normalize('NFC', k): normalize_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [normalize_dict(item) for item in d]
    elif isinstance(d, str):
        return unicodedata.normalize('NFC', d)
    else:
        return d


@api_bp.route('/api/movies')
def api_movies():
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401

    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    categorias_lista, series = media_service.list_content(force_refresh=force_refresh)
    
    # Normalizar cada elemento de la lista
    categorias_normalizadas = []
    for cat, pelis in categorias_lista:
        categorias_normalizadas.append([
            normalize_dict(cat),
            [normalize_dict(p) for p in pelis]
        ])
    
    series = normalize_dict(series)

    response = jsonify({
        "categorias": categorias_normalizadas,
        "series": series
    })
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response
    

@api_bp.route('/api/thumbnail-status')
def thumbnail_status():
    """API de estado de thumbnails"""
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    
    status = media_service.get_thumbnail_status()
    status["timestamp"] = time.time()
    
    response = jsonify(status)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Cache-Control'] = 'no-cache'
    return response
