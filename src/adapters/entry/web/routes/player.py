"""
Adaptador de entrada - Rutas de reproductor
Blueprint para streaming y seguimiento de progreso
"""
import os
import re
import urllib.parse
from flask import Blueprint, jsonify, request, session, Response, stream_with_context, render_template

# Importar casos de uso (se inicializan después)
from src.core.use_cases.player import (
    StreamMovieUseCase,
    StreamEpisodeUseCase,
    TrackProgressUseCase,
    GetContinueWatchingUseCase,
    GetWatchedContentUseCase
)

logger = None


def setup_logging(log_folder):
    """Setup de logging - se configurará después"""
    import logging
    global logger
    if logger is None:
        logger = logging.getLogger(__name__)
    return logger


player_bp = Blueprint('player', __name__)

# Blueprint para la página de reproducción (sin prefijo /api)
player_page_bp = Blueprint('player_page', __name__)


def clean_filename(filename):
    """Limpia el nombre del archivo para mostrar"""
    name = re.sub(r'[-_]?optimized', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'\.(mkv|mp4|avi|mov)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[._-]', ' ', name)
    return ' '.join(word.capitalize() for word in name.split())


@player_page_bp.route('/play/<path:media_path>')
def play_page(media_path):
    """Página de reproducción de video - versión simple sin bloqueos"""
    # URL decode the path
    filename = urllib.parse.unquote(media_path)
    
    # Limpiar el nombre para mostrar
    basename = os.path.basename(filename)
    sanitized_name = clean_filename(basename)
    
    # Extraer año para la búsqueda de metadatos (se envía al cliente)
    year = None
    year_match = re.search(r'\((\d{4})\)', basename)
    if year_match:
        year = int(year_match.group(1))
    
    # Extraer título limpio
    clean_title = re.sub(r'\(.*?\)', '', basename)
    clean_title = re.sub(r'[-_]?optimized', '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'\.(mkv|mp4|avi|mov)$', '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'[._-]', ' ', clean_title).strip()
    
    return render_template('play.html', 
                           filename=filename,
                           sanitized_name=sanitized_name,
                           media_path=media_path,
                           clean_title=clean_title,
                           year=year)


@player_page_bp.route('/play/id/<movie_id>')
def play_page_by_id(movie_id):
    """Página de reproducción usando ID de película"""
    from src.adapters.config.dependencies import get_movie_repository
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🎬 play_page_by_id: {movie_id}")
    
    try:
        repo = get_movie_repository()
        movie = repo.get_by_id(movie_id)
        
        if not movie:
            logger.warning(f"⚠️ Película no encontrada: {movie_id}")
            return "Película no encontrada", 404
        
        filename = movie['path']
        basename = os.path.basename(filename)
        sanitized_name = clean_filename(basename)
        
        year = movie.get('year')
        clean_title = movie.get('title', sanitized_name)
        
        logger.info(f"✅ Reproduciendo: {clean_title} ({year})")
        
        return render_template('play.html', 
                               filename=filename,
                               sanitized_name=sanitized_name,
                               media_path=movie_id,
                               clean_title=clean_title,
                               year=year,
                               movie_id=movie_id)
    
    except Exception as e:
        logger.error(f"❌ Error en play_page_by_id: {e}")
        return f"Error: {str(e)}", 500


@player_page_bp.route('/play')
def play_page_root():
    """Página de reproducción (raíz)"""
    return render_template('play.html', 
                           filename='',
                           sanitized_name='Reproducción',
                           media_path='')

# Casos de uso inyectados
_stream_movie_use_case = None
_stream_episode_use_case = None
_track_progress_use_case = None
_get_continue_watching_use_case = None
_get_watched_content_use_case = None


def init_player_routes(
    stream_movie_use_case: StreamMovieUseCase = None,
    stream_episode_use_case: StreamEpisodeUseCase = None,
    track_progress_use_case: TrackProgressUseCase = None,
    get_continue_watching_use_case: GetContinueWatchingUseCase = None,
    get_watched_content_use_case: GetWatchedContentUseCase = None
):
    """Inicializa los casos de uso para las rutas de reproductor"""
    global _stream_movie_use_case, _stream_episode_use_case
    global _track_progress_use_case, _get_continue_watching_use_case
    global _get_watched_content_use_case
    
    _stream_movie_use_case = stream_movie_use_case
    _stream_episode_use_case = stream_episode_use_case
    _track_progress_use_case = track_progress_use_case
    _get_continue_watching_use_case = get_continue_watching_use_case
    _get_watched_content_use_case = get_watched_content_use_case


def get_user_id():
    """Obtiene el ID del usuario de la sesión"""
    # Por ahora devuelve 0 para usuario anónimo
    # TODO: Implementar con autenticación real
    return session.get('user_id', 0)


# === ENDPOINTS DE METADATOS (ASÍNCRONO) ===

@player_bp.route('/api/movie/metadata', methods=['GET'])
def get_movie_metadata():
    """Endpoint para obtener metadatos de una película de forma asíncrona"""
    title = request.args.get('title', '')
    year = request.args.get('year', type=int)
    
    if not title:
        return jsonify({'error': 'title es requerido'}), 400
    
    movie_info = None
    try:
        from src.adapters.outgoing.services.omdb.client import OMDBMetadataService
        omdb_service = OMDBMetadataService()
        
        if omdb_service.is_available():
            omdb_data = omdb_service.get_movie_metadata(title, year)
            
            if omdb_data:
                movie_info = {
                    'title': omdb_data.get('Title'),
                    'year': omdb_data.get('Year'),
                    'released': omdb_data.get('Released'),
                    'runtime': omdb_data.get('Runtime'),
                    'genre': omdb_data.get('Genre'),
                    'genres': [g.strip() for g in omdb_data.get('Genre', '').split(',') if g.strip()],
                    'director': omdb_data.get('Director'),
                    'writer': omdb_data.get('Writer'),
                    'actors': omdb_data.get('Actors'),
                    'plot': omdb_data.get('Plot'),
                    'language': omdb_data.get('Language'),
                    'country': omdb_data.get('Country'),
                    'awards': omdb_data.get('Awards'),
                    'imdb_rating': omdb_data.get('imdbRating'),
                    'imdb_votes': omdb_data.get('imdbVotes'),
                    'box_office': omdb_data.get('BoxOffice'),
                }
                
                # Procesar póster
                poster = omdb_data.get('Poster')
                if poster and poster != 'N/A':
                    import requests
                    movie_info['poster'] = [
                        f"/proxy-image?url={requests.utils.quote(poster)}",
                        '/static/images/default-poster.jpg'
                    ]
                else:
                    movie_info['poster'] = None
                
                # Procesar ratings
                ratings = []
                for rating in omdb_data.get('Ratings', []):
                    source = rating.get('Source', '')
                    value = rating.get('Value', '')
                    if 'Rotten Tomatoes' in source:
                        ratings.append(f"🍅 {value}")
                    elif 'Metacritic' in source:
                        ratings.append(f"📊 {value}")
                    elif 'Internet Movie Database' in source:
                        ratings.append(f"⭐ {value}")
                movie_info['ratings'] = ratings
                
                # Procesar reparto
                movie_info['cast'] = [a.strip() for a in omdb_data.get('Actors', '').split(',')[:5] if a.strip()]
        
        if movie_info:
            return jsonify(movie_info)
        else:
            return jsonify({'error': 'No se encontraron metadatos'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === ENDPOINTS DE STREAMING ===

@player_bp.route('/api/stream/movie/<int:movie_id>', methods=['GET'])
def stream_movie(movie_id):
    """Endpoint para obtener información de streaming de película"""
    global _stream_movie_use_case
    
    if _stream_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        stream_info = _stream_movie_use_case.execute(movie_id)
        
        if not stream_info:
            return jsonify({'error': 'Película no encontrada'}), 404
        
        return jsonify(stream_info)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@player_bp.route('/api/stream/episode/<int:episode_id>', methods=['GET'])
def stream_episode(episode_id):
    """Endpoint para obtener información de streaming de episodio"""
    global _stream_episode_use_case
    
    if _stream_episode_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        stream_info = _stream_episode_use_case.execute(episode_id)
        
        if not stream_info:
            return jsonify({'error': 'Episodio no encontrado'}), 404
        
        return jsonify(stream_info)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === ENDPOINTS DE PROGRESO ===

@player_bp.route('/api/progress', methods=['POST'])
def update_progress():
    """Actualiza el progreso de reproducción"""
    global _track_progress_use_case
    
    if _track_progress_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        user_id = get_user_id()
        media_type = data.get('media_type', 'movie')
        media_id = data.get('media_id')
        position = data.get('position', 0)
        duration = data.get('duration', 0)
        
        if not media_id:
            return jsonify({'error': 'media_id es requerido'}), 400
        
        progress = _track_progress_use_case.update_position(
            user_id=user_id,
            media_type=media_type,
            media_id=media_id,
            position=position,
            duration=duration
        )
        
        return jsonify(progress)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@player_bp.route('/api/progress/complete', methods=['POST'])
def mark_completed():
    """Marca un contenido como completado"""
    global _track_progress_use_case
    
    if _track_progress_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        user_id = get_user_id()
        media_type = data.get('media_type', 'movie')
        media_id = data.get('media_id')
        
        if not media_id:
            return jsonify({'error': 'media_id es requerido'}), 400
        
        progress = _track_progress_use_case.mark_completed(
            user_id=user_id,
            media_type=media_type,
            media_id=media_id
        )
        
        return jsonify(progress)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@player_bp.route('/api/progress/<media_type>/<int:media_id>', methods=['GET'])
def get_progress(media_type, media_id):
    """Obtiene el progreso de un contenido específico"""
    global _track_progress_use_case
    
    if _track_progress_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        user_id = get_user_id()
        
        progress = _track_progress_use_case.get_progress(
            user_id=user_id,
            media_type=media_type,
            media_id=media_id
        )
        
        if not progress:
            return jsonify({
                'position': 0,
                'duration': 0,
                'is_completed': False
            })
        
        return jsonify(progress)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === ENDPOINTS DE "SEGUIR VIENDO" ===

@player_bp.route('/api/continue-watching', methods=['GET'])
def get_continue_watching():
    """Obtiene los contenidos que el usuario está viendo"""
    global _get_continue_watching_use_case
    
    if _get_continue_watching_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        user_id = get_user_id()
        limit = request.args.get('limit', 10, type=int)
        
        content = _get_continue_watching_use_case.execute(
            user_id=user_id,
            limit=limit
        )
        
        return jsonify(content)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@player_bp.route('/api/watched', methods=['GET'])
def get_watched():
    """Obtiene los contenidos vistos por el usuario"""
    global _get_watched_content_use_case
    
    if _get_watched_content_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        user_id = get_user_id()
        limit = request.args.get('limit', 20, type=int)
        
        content = _get_watched_content_use_case.execute(
            user_id=user_id,
            limit=limit
        )
        
        return jsonify(content)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
