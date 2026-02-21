"""
Adaptador de entrada - Rutas de catálogo
Blueprint para /api/movies y endpoints relacionados
"""
import unicodedata
import os
from flask import Blueprint, jsonify, request

from src.core.use_cases.catalog import ListMoviesUseCase, ListSeriesUseCase, SearchUseCase

logger = None


def setup_logging(log_folder):
    """Setup de logging - se configurará después"""
    import logging
    global logger
    if logger is None:
        logger = logging.getLogger(__name__)
    return logger


catalog_bp = Blueprint('catalog', __name__)

# Casos de uso inyectados
_list_movies_use_case = None
_list_series_use_case = None
_search_use_case = None


def init_catalog_routes(
    list_movies_use_case: ListMoviesUseCase = None,
    list_series_use_case: ListSeriesUseCase = None,
    search_use_case: SearchUseCase = None
):
    """Inicializa los casos de uso para las rutas de catálogo"""
    global _list_movies_use_case, _list_series_use_case, _search_use_case
    _list_movies_use_case = list_movies_use_case
    _list_series_use_case = list_series_use_case
    _search_use_case = search_use_case


def normalize_dict(d):
    """Normaliza caracteres Unicode en diccionarios"""
    if isinstance(d, dict):
        return {unicodedata.normalize('NFC', str(k)): normalize_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [normalize_dict(item) for item in d]
    elif isinstance(d, str):
        return unicodedata.normalize('NFC', d)
    else:
        return d


@catalog_bp.route('/api/movies', methods=['GET'])
def get_movies():
    """Obtiene la lista de películas agrupadas por categorías"""
    global _list_movies_use_case, _list_series_use_case
    
    if _list_movies_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        # Parámetros de query
        genre = request.args.get('genre')
        year = request.args.get('year')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        random = request.args.get('random', 'false').lower() == 'true'
        
        if random:
            movies = _list_movies_use_case.get_random(limit=limit or 10)
        else:
            movies = _list_movies_use_case.execute(
                genre=genre,
                year=int(year) if year else None,
                limit=limit,
                offset=offset
            )
        
        # Agrupar películas por categoría (basado en la ruta)
        categorias = []
        
        # Obtener películas nuevas para el carrusel de Novedades
        # Filtrar películas de los últimos 30 días
        new_movies = [m for m in movies if m.get('is_new', False)]
        # Ordenar por days_ago (más recientes primero)
        new_movies.sort(key=lambda x: x.get('days_ago', 999))
        
        # Agregar carrusel de Novedades al inicio si hay películas nuevas
        if new_movies:
            categorias.insert(0, ['Novedades', new_movies[:20]])  # Máximo 20 películas nuevas
        
        # Agrupar el resto de películas por categoría
        for movie in movies:
            # Extraer categoría de la ruta
            path = movie.get('path', '')
            parts = path.split('/')
            if len(parts) > 1:
                # La categoría es el penúltimo directorio (después de 'mkv')
                if 'mkv' in parts:
                    idx = parts.index('mkv')
                    if idx + 1 < len(parts):
                        categoria = parts[idx + 1]
                    else:
                        categoria = 'Otros'
                else:
                    categoria = 'Otros'
            else:
                categoria = 'Otros'
            
            # Buscar si ya existe la categoría
            found = False
            for cat in categorias:
                if cat[0] == categoria:
                    cat[1].append(movie)
                    found = True
                    break
            if not found:
                categorias.append([categoria, [movie]])
        
        # Obtener series
        series = {}
        if _list_series_use_case:
            raw_series = _list_series_use_case.execute()
            # Agrupar por nombre de serie - el caso de uso ya devuelve el nombre
            for serie in raw_series:
                # Usar el nombre directo del caso de uso
                serie_name = serie.get('name', 'Unknown')
                
                if serie_name not in series:
                    series[serie_name] = []
                
                # Agregar los episodios de esta serie
                if 'episodes' in serie:
                    series[serie_name].extend(serie['episodes'])
                else:
                    series[serie_name].append(serie)
        
        # Devolver estructura esperada por el frontend
        return jsonify(normalize_dict({
            'categorias': categorias,
            'series': series
        }))
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@catalog_bp.route('/api/series', methods=['GET'])
def get_series():
    """Obtiene la lista de series"""
    global _list_series_use_case
    
    if _list_series_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        genre = request.args.get('genre')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        series = _list_series_use_case.execute(
            genre=genre,
            limit=limit,
            offset=offset
        )
        
        return jsonify(normalize_dict(series))
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@catalog_bp.route('/api/search', methods=['GET'])
def search_content():
    """Busca contenido en el catálogo"""
    global _search_use_case
    
    if _search_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({'error': 'Query no proporcionada'}), 400
        
        results = _search_use_case.execute(query)
        
        return jsonify(normalize_dict(results))
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@catalog_bp.route('/api/movie-thumbnail/<filename>', methods=['GET'])
def get_movie_thumbnail(filename):
    """Obtiene el thumbnail de una película"""
    # Este endpoint se manejará en otro archivo (thumbnails)
    return jsonify({'error': 'Endpoint no implementado en este blueprint'}), 501


@catalog_bp.route('/api/movie-thumbnail', methods=['GET'])
def get_movie_thumbnail_by_title():
    """Obtiene el thumbnail de una película por título (query param)"""
    from src.adapters.config.dependencies import get_metadata_service
    
    title = request.args.get('title')
    year = request.args.get('year')
    
    if not title:
        return jsonify({'error': 'Título no proporcionado'}), 400
    
    metadata_service = get_metadata_service()
    if not metadata_service:
        return jsonify({'error': 'Servicio de metadatos no disponible'}), 500
    
    try:
        year_int = int(year) if year else None
        thumbnail = metadata_service.get_movie_thumbnail(title, year_int)
        if thumbnail:
            return jsonify({'thumbnail': thumbnail})
        return jsonify({'error': 'Thumbnail no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@catalog_bp.route('/api/serie-poster', methods=['GET'])
def get_serie_poster():
    """Obtiene el póster de una serie por nombre"""
    from src.adapters.config.dependencies import get_metadata_service
    
    name = request.args.get('name')
    
    if not name:
        return jsonify({'error': 'Nombre de serie no proporcionado'}), 400
    
    metadata_service = get_metadata_service()
    if not metadata_service:
        return jsonify({'error': 'Servicio de metadatos no disponible'}), 500
    
    try:
        poster = metadata_service.get_serie_poster(name)
        if poster:
            return jsonify({'poster': poster})
        return jsonify({'error': 'Póster no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
