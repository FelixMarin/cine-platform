"""
Rutas de API - Endpoints JSON
"""
from flask import Blueprint, jsonify, request
from src.adapters.config.dependencies import (
    get_list_movies_use_case,
    get_search_use_case,
    get_continue_watching_use_case,
    get_track_progress_use_case
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def init_api_routes():
    """Inicializa las rutas de API"""
    pass


@api_bp.route('/movies', methods=['GET'])
def list_movies():
    """Lista todas las películas"""
    use_case = get_list_movies_use_case()
    if use_case:
        movies = use_case.execute()
        return jsonify({'movies': [m.to_dict() for m in movies]})
    return jsonify({'error': 'Service not available'}), 503


@api_bp.route('/search', methods=['GET'])
def search():
    """Búsqueda de contenido"""
    query = request.args.get('q', '')
    use_case = get_search_use_case()
    if use_case and query:
        results = use_case.execute(query)
        return jsonify({'results': results})
    return jsonify({'results': []})


@api_bp.route('/continue-watching', methods=['GET'])
def continue_watching():
    """Contenido en progreso"""
    use_case = get_continue_watching_use_case()
    if use_case:
        # Por ahora retorna lista vacía si no hay usuario
        content = use_case.execute(user_id=1)
        return jsonify({'content': content})
    return jsonify({'error': 'Service not available'}), 503


@api_bp.route('/progress', methods=['POST'])
def update_progress():
    """Actualiza progreso de reproducción"""
    data = request.get_json()
    use_case = get_track_progress_use_case()
    if use_case and data:
        use_case.update_position(
            user_id=data.get('user_id', 1),
            media_id=data.get('media_id'),
            media_type=data.get('media_type', 'movie'),
            position=data.get('position', 0),
            duration=data.get('duration', 0)
        )
        return jsonify({'success': True})
    return jsonify({'error': 'Service not available'}), 503


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok'})
