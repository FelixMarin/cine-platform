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


@catalog_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """Obtiene todas las categorías con películas y series"""
    try:
        # Obtener películas
        movies = _list_movies_use_case.execute() if _list_movies_use_case else []
        
        # Obtener series
        series = _list_series_use_case.execute() if _list_series_use_case else []
        
        return jsonify({
            'movies': movies,
            'series': series
        })
    except Exception as e:
        import logging
        logging.error(f"Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500


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
    
    # Crear logger local
    import logging
    import traceback
    import time
    logger = logging.getLogger(__name__)
    
    start_total = time.time()
    logger.info("=== GET /api/movies ===")
    
    if _list_movies_use_case is None:
        logger.error("❌ _list_movies_use_case es None")
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        # PASO 1: Obtener películas
        start_step1 = time.time()
        movies = _list_movies_use_case.execute()
        step1_time = time.time() - start_step1
        logger.info(f"⏱️ PASO 1 (execute): {step1_time:.2f}s - {len(movies)} películas")
        
        # Verificar tipo
        if movies is None:
            movies = []
        elif not isinstance(movies, list):
            movies = list(movies) if movies else []
        
        # PASO 2: Filtrar nuevas
        start_step2 = time.time()
        new_movies = []
        for m in movies:
            try:
                if isinstance(m, dict) and m.get('is_new', False):
                    new_movies.append(m)
            except Exception:
                pass
        new_movies.sort(key=lambda x: x.get('days_ago', 999))
        step2_time = time.time() - start_step2
        logger.info(f"⏱️ PASO 2 (filtrar nuevas): {step2_time:.2f}s - {len(new_movies)} nuevas")
        
        # PASO 3: Construir categorías
        start_step3 = time.time()
        categorias = []
        
        if new_movies:
            categorias.append(['Novedades', new_movies[:20]])
        
        # Agrupar por categoría
        categorias_dict = {}
        for movie in movies:
            if not isinstance(movie, dict):
                continue
            path = movie.get('path', '')
            if not path:
                categoria = 'Otros'
            else:
                parts = str(path).split('/')
                if 'mkv' in parts:
                    idx = parts.index('mkv')
                    categoria = parts[idx + 1] if idx + 1 < len(parts) else 'Otros'
                else:
                    categoria = 'Otros'
            
            if categoria not in categorias_dict:
                categorias_dict[categoria] = []
            categorias_dict[categoria].append(movie)
        
        for cat_name, cat_movies in categorias_dict.items():
            categorias.append([cat_name, cat_movies])
        
        step3_time = time.time() - start_step3
        logger.info(f"⏱️ PASO 3 (categorizar): {step3_time:.2f}s - {len(categorias)} categorías")
        
        # PASO 4: Obtener series
        start_step4 = time.time()
        series = {}
        if _list_series_use_case:
            try:
                raw_series = _list_series_use_case.execute()
                for serie in raw_series:
                    serie_name = serie.get('name', 'Unknown')
                    if serie_name not in series:
                        series[serie_name] = []
                    if 'episodes' in serie:
                        series[serie_name].extend(serie['episodes'])
                    else:
                        series[serie_name].append(serie)
            except Exception as e:
                logger.error(f"❌ Error obteniendo series: {e}")
        step4_time = time.time() - start_step4
        logger.info(f"⏱️ PASO 4 (series): {step4_time:.2f}s")
        
        # PASO 5: Normalizar
        start_step5 = time.time()
        response_data = {
            'categorias': categorias,
            'series': series
        }
        normalized = normalize_dict(response_data)
        step5_time = time.time() - start_step5
        logger.info(f"⏱️ PASO 5 (normalizar): {step5_time:.2f}s")
        
        total_time = time.time() - start_total
        logger.info(f"⏱️ TOTAL: {total_time:.2f}s")
        
        return jsonify(normalized)
    
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO en /api/movies: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# Endpoint de debug ultra-simple
@catalog_bp.route('/api/movies-test', methods=['GET'])
def get_movies_test():
    """Versión ultra simple para debug"""
    global _list_movies_use_case
    import traceback
    
    try:
        if _list_movies_use_case is None:
            return jsonify({'error': 'No inicializado'}), 500
        
        movies = _list_movies_use_case.execute()
        
        return jsonify({
            'total': len(movies) if movies else 0,
            'first': movies[0] if movies else None,
            'type': str(type(movies))
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500


# Endpoint de debug del repositorio
@catalog_bp.route('/api/debug/repo', methods=['GET'])
def debug_repo():
    """Endpoint para diagnosticar el repositorio"""
    from src.adapters.config.dependencies import get_movie_repository
    import traceback
    
    try:
        repo = get_movie_repository()
        if repo is None:
            return jsonify({'error': 'Repositorio no inicializado'}), 500
        
        movies = repo.list_all()
        
        return jsonify({
            'success': True,
            'count': len(movies) if movies else 0,
            'first_movie': movies[0] if movies else None,
            'cache_stats': repo.get_cache_stats() if hasattr(repo, 'get_cache_stats') else {}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500
        
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
        
        logger.info(f"✅ Categorías generadas: {len(categorias)}")
        logger.info(f"📦 Estructura final: {{'categorias': {len(categorias)}, 'series': {len(series)}}}")
        
        # Devolver estructura esperada por el frontend
        return jsonify(normalize_dict({
            'categorias': categorias,
            'series': series
        }))
    
    except Exception as e:
        logger.error(f"❌ Error en /api/movies: {e}", exc_info=True)
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
