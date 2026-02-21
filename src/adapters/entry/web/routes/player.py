"""
Adaptador de entrada - Rutas de reproductor
Blueprint para streaming y seguimiento de progreso
"""
import os
from flask import Blueprint, jsonify, request, session, Response, stream_with_context

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
