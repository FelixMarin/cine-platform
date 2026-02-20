# modules/routes/api.py
"""
Blueprint de API: /api/movies, /api/movie-thumbnail
"""
import unicodedata
import time
import os
import re
from flask import Blueprint, session, jsonify, request
from modules.logging.logging_config import setup_logging

# Importar OMDBClient (¡esto faltaba!)
from modules.omdb_client import OMDBClient

logger = setup_logging(os.environ.get("LOG_FOLDER"))

api_bp = Blueprint('api', __name__)

# Servicios inyectados desde fuera
media_service = None
omdb_client = None  # ¡Esto faltaba!


def init_services(media_svc, omdb_svc=None):  # ¡Esta función faltaba!
    """Inicializa los servicios"""
    global media_service, omdb_client
    media_service = media_svc
    omdb_client = omdb_svc
    logger.info("✅ Servicios de API inicializados")


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

def clean_movie_title(title: str) -> str:
    """
    Limpia el título de una película eliminando sufijos y fechas.
    """
    if not title:
        return title
    
    logger.debug(f"🧹 Limpiando título: '{title}'")
    
    # Paso 1: Eliminar sufijos
    clean = title.replace('-optimized', '').replace('_optimized', '')
    logger.debug(f"   Después de quitar sufijos: '{clean}'")
    
    # Paso 2: Eliminar fecha (YYYY)
    clean = re.sub(r'\(\d{4}\)', '', clean)
    logger.debug(f"   Después de quitar fecha: '{clean}'")
    
    # Paso 3: Limpiar espacios y guiones
    clean = clean.replace('-', ' ').replace('_', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    logger.debug(f"✅ Título limpio: '{clean}'")
    
    return clean

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
 

@api_bp.route('/api/movie-thumbnail')
def movie_thumbnail():
    """Endpoint para obtener thumbnail de una película por título"""
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    
    # Verificar que omdb_client está inicializado
    if omdb_client is None:
        logger.error("❌ OMDBClient no inicializado")
        return jsonify({"error": "Servicio de thumbnails no disponible"}), 503
    
    title = request.args.get('title')
    year = request.args.get('year', type=int)
    
    if not title:
        return jsonify({"error": "Título requerido"}), 400
    
    # Log para depuración
    logger.info(f"📸 Solicitando thumbnail para: '{title}' (año: {year})")
    
    # Limpiar título
    clean_title = clean_movie_title(title)
    
    try:
        # Intentar obtener thumbnail
        thumbnail_url = omdb_client.get_movie_thumbnail(clean_title, year)
        
        if thumbnail_url:
            logger.info(f"✅ Thumbnail encontrado para: {clean_title}")
            return jsonify({"thumbnail": thumbnail_url})
        else:
            logger.info(f"❌ No se encontró thumbnail para: {clean_title}")
            return jsonify({"thumbnail": None}), 404
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo thumbnail: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor"}), 500