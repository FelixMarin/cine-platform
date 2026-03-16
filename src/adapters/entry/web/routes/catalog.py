"""
Adaptador de entrada - Rutas de catálogo
Blueprint para /api/movies y endpoints relacionados
"""
import unicodedata
import os
from flask import Blueprint, jsonify, request
from src.adapters.entry.web.middleware.auth_middleware import require_auth

from src.core.use_cases.catalog import ListMoviesUseCase, ListSeriesUseCase, SearchUseCase

from src.infrastructure.logging import setup_logging
logger = setup_logging(os.environ.get("LOG_FOLDER"))


catalog_bp = Blueprint('catalog', __name__, url_prefix='')

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
@require_auth
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
        
        # === LOGS DE DEPURACIÓN ===
        logger.info(f"🔍 Movies tipo: {type(movies)}")
        if movies:
            logger.info(f"🔍 Primera película: {movies[0]}")
        # ===========================
        
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
        
        # === LOGS DE DEPURACIÓN ===
        logger.info(f"🔍 Response categorias: {len(categorias)} categorías")
        logger.info(f"🔍 Response series: {len(series)} series")
        if categorias:
            logger.info(f"🔍 Primera categoría: {categorias[0]}")
        # ===========================
        
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
    import os
    
    # Añadir logs de debug
    logger.info(f"🔍 DEBUG: MOVIES_FOLDER env = {os.environ.get('MOVIES_FOLDER')}")
    logger.info(f"🔍 DEBUG: Base folder path = {os.environ.get('MOVIES_FOLDER')}")
    
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
    """
    Obtiene el thumbnail de una película por título (query param).
    
    Flujo (prioridad de fuentes):
        1. Base de datos (poster_image de omdb_entries) - FUENTE PRIMARIA
        2. Base de datos (poster_image de local_content) - FALLBACK PARA CONTENIDO SIN IMDB
        3. OMDB API + guardar en BD (si no hay en BD)
        4. Sistema de archivos local (thumbnails manuales) - FALLBACK
        
    El servicio DatabaseThumbnailService es la fuente primaria que busca
    directamente en el campo poster_image de las tablas omdb_entries y local_content.
    """
    import logging
    import io
    from flask import send_file
    
    logger = logging.getLogger(__name__)
    
    # Importar servicios de thumbnails
    from src.adapters.config.dependencies import get_database_thumbnail_service
    from src.adapters.outgoing.services.omdb.thumbnail_provider import get_omdb_thumbnail_provider
    from src.adapters.outgoing.services.thumbnails.local_search import get_local_thumbnail_search
    
    # Obtener servicios
    db_thumbnail_service = get_database_thumbnail_service()
    omdb_provider = get_omdb_thumbnail_provider()
    local_search = get_local_thumbnail_search()
    
    # === 1. Validar parámetros ===
    title = request.args.get('title')
    year = request.args.get('year')
    filename = request.args.get('filename')
    
    if not title:
        return jsonify({'error': 'Titulo no proporcionado'}), 400
    
    logger.info(f"Buscando thumbnail para: [{title}] año=[{year}]")
    
    # === 2. FUENTE PRIMARIA: Buscar en base de datos (poster_image) ===
    thumbnail_data = db_thumbnail_service.get_thumbnail_from_db(title, year)
    
    if thumbnail_data:
        return send_file(
            io.BytesIO(thumbnail_data),
            mimetype='image/jpeg',
            as_attachment=False,
            max_age=86400  # Cache 24h en navegador
        )
    
    # === 3. Si no hay en BD, intentar obtener de OMDB (y guardar en BD) ===
    logger.info(f"DB: No se encontró en BD, intentando OMDB para [{title}]")
    thumbnail_data = omdb_provider.fetch_thumbnail_data(title, year)
    
    if thumbnail_data:
        logger.info(f"OMDB: Poster obtenido para [{title}] y guardado en BD")
        return send_file(
            io.BytesIO(thumbnail_data),
            mimetype='image/jpeg',
            as_attachment=False,
            max_age=86400  # Cache 24h en navegador
        )
    
    # === 4. FALLBACK FINAL: Buscar en sistema de archivos local ===
    logger.info(f"OMDB: No se encontró, buscando thumbnail local para [{title}]")
    local_thumbnail = local_search.search_local_thumbnail(title, filename)
    
    if local_thumbnail:
        return jsonify({'thumbnail': local_thumbnail})
    
    # === 5. Si no se encontró en ningún lado, devolver 404 ===
    logger.info(f"❌ Sin datos: thumbnail no encontrado para [{title}]")
    return jsonify({'error': 'Thumbnail no encontrado'}), 404


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
