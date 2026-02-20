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
 

# modules/routes/api.py

@api_bp.route('/api/movie-thumbnail')
def movie_thumbnail():
    """Endpoint para obtener thumbnail de una película por título"""
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    
    title = request.args.get('title')
    year = request.args.get('year', type=int)
    filename = request.args.get('filename')  # Nuevo parámetro
    
    if not title:
        return jsonify({"error": "Título requerido"}), 400
    
    # 1. Intentar con OMDB
    thumbnail_url = omdb_client.get_movie_thumbnail(title, year)
    
    if thumbnail_url:
        logger.info(f"✅ Thumbnail OMDB encontrado para: {title}")
        return jsonify({"thumbnail": thumbnail_url})
    
    # 2. Si OMDB falla, buscar thumbnail local
    if filename:
        # Construir nombre base del archivo
        base_name = os.path.splitext(filename)[0]
        
        # Probar con .jpg primero, luego .webp (el frontend probará con onerror)
        local_jpg = f"/thumbnails/{base_name}.jpg"
        local_webp = f"/thumbnails/{base_name}.webp"
        
        logger.info(f"📁 OMDB no encontró, probando thumbnail local: {base_name}")
        
        # Devolvemos la ruta JPG (el frontend probará si existe)
        return jsonify({"thumbnail": local_jpg})
    
    # 3. Si no hay filename, devolver 404
    return jsonify({"thumbnail": None}), 404


@api_bp.route('/api/serie-poster')
def serie_poster():
    """Endpoint para obtener póster de una serie"""
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    
    serie_name = request.args.get('name')
    if not serie_name:
        return jsonify({"error": "Nombre de serie requerido"}), 400
    
    # Limpiar nombre
    clean_name = serie_name.strip()
    
    # 1. Intentar con OMDB
    poster_url = omdb_client.get_serie_poster(clean_name)
    
    if poster_url:
        return jsonify({"poster": poster_url})
    
    # 2. Si no, devolver 404 (el frontend usará default.jpg)
    return jsonify({"poster": None}), 404