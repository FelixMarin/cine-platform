"""
Adaptador de entrada - Rutas del optimizador
Blueprint para /api/optimizer y /optimizer
"""
import os

from flask import Blueprint, jsonify, render_template, request

from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role
from src.application.use_cases.optimizer import EstimateSizeUseCase, OptimizeMovieUseCase
from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


optimizer_bp = Blueprint('optimizer', __name__)

# Ruta para la página HTML del optimizador (sin prefijo /api)
optimizer_page_bp = Blueprint('optimizer_page', __name__)

@optimizer_page_bp.route('/optimizer')
@require_role('admin')
def optimizer_page():
    """Página del optimizador de video"""
    return render_template('pages/optimizer/index.html')


@optimizer_page_bp.route('/optimizer/profiles')
@require_role('admin')
def optimizer_profiles():
    """API de perfiles del optimizador"""
    from flask import jsonify
    # Perfiles de optimización
    profiles = {
        "ultra_fast": {
            "name": "ultra_fast",
            "description": "📱 Móvil/3G - 360p (500 kbps)",
            "preset": "veryfast",
            "video_bitrate": "500k",
            "audio_bitrate": "96k",
            "resolution": "640:360",
            "maxrate": "750k"
        },
        "fast": {
            "name": "fast",
            "description": "📱 Tablet/4G - 480p (1 Mbps)",
            "preset": "veryfast",
            "video_bitrate": "1000k",
            "audio_bitrate": "128k",
            "resolution": "854:480",
            "maxrate": "1500k"
        },
        "balanced": {
            "name": "balanced",
            "description": "💻 WiFi - 720p (2 Mbps)",
            "preset": "medium",
            "video_bitrate": "2000k",
            "audio_bitrate": "128k",
            "resolution": "1280:720",
            "maxrate": "3000k"
        },
        "high_quality": {
            "name": "high_quality",
            "description": "🚀 Fibra - 1080p (4 Mbps)",
            "preset": "slow",
            "video_bitrate": "4000k",
            "audio_bitrate": "192k",
            "resolution": "1920:1080",
            "maxrate": "6000k"
        },
        "master": {
            "name": "master",
            "description": "🎬 4K - Calidad original (8 Mbps)",
            "preset": "slow",
            "video_bitrate": "8000k",
            "audio_bitrate": "256k",
            "resolution": "Original",
            "maxrate": "12000k"
        }
    }
    return jsonify(profiles)


@optimizer_page_bp.route('/process-file', methods=['POST'])
def process_file():
    """Procesa un archivo de video para optimización"""
    import os

    from flask import jsonify, request

    # Obtener la carpeta de uploads desde variables de entorno
    upload_folder = os.environ.get('UPLOAD_FOLDER', '/home/jetson/Public/cine-app/cine-platform/uploads')

    if 'file' not in request.files:
        return jsonify({'error': 'No se ha proporcionado ningún archivo'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No se ha seleccionado ningún archivo'}), 400

    try:
        # Guardar el archivo
        filename = file.filename
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Obtener perfil
        profile = request.form.get('profile', 'balanced')

        # Notificar que el archivo está listo para procesar
        return jsonify({
            'success': True,
            'message': f'Archivo {filename} subido correctamente',
            'file_path': filepath,
            'profile': profile
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Casos de uso inyectados
_optimize_movie_use_case = None
_estimate_size_use_case = None


def init_optimizer_routes(
    optimize_movie_use_case: OptimizeMovieUseCase = None,
    estimate_size_use_case: EstimateSizeUseCase = None
):
    """Inicializa los casos de uso para las rutas del optimizador"""
    global _optimize_movie_use_case, _estimate_size_use_case
    _optimize_movie_use_case = optimize_movie_use_case
    _estimate_size_use_case = estimate_size_use_case


@optimizer_bp.route('/api/optimizer/optimize', methods=['POST'])
def optimize_video():
    """Añade un video a la cola de optimización"""
    global _optimize_movie_use_case

    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500

    try:
        data = request.get_json()

        file_path = data.get('file_path')
        profile = data.get('profile', 'balanced')

        if not file_path:
            return jsonify({'error': 'file_path es requerido'}), 400

        result = _optimize_movie_use_case.execute(file_path, profile)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/optimize-folder', methods=['POST'])
def optimize_folder():
    """Añade todos los videos de una carpeta a la cola"""
    global _optimize_movie_use_case

    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500

    try:
        data = request.get_json()

        folder_path = data.get('folder_path')
        profile = data.get('profile', 'balanced')

        if not folder_path:
            return jsonify({'error': 'folder_path es requerido'}), 400

        result = _optimize_movie_use_case.process_folder(folder_path, profile)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/status', methods=['GET'])
def get_status():
    """Obtiene el estado actual del optimizador"""
    global _optimize_movie_use_case

    # Si no hay caso de uso, devolver estado simple
    if _optimize_movie_use_case is None:
        return jsonify({
            'status': 'not_initialized',
            'current_video': None,
            'current_step': 0,
            'history': [],
            'message': 'Optimizador no disponible'
        })

    try:
        status = _optimize_movie_use_case.get_status()

        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/cancel', methods=['POST'])
@require_auth
@require_role('admin')
def cancel_current():
    """Cancela el procesamiento actual"""
    global _optimize_movie_use_case

    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500

    try:
        success = _optimize_movie_use_case.cancel_current()

        return jsonify({'success': success})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/profiles', methods=['GET'])
def get_profiles():
    """Obtiene los perfiles de optimización disponibles"""
    global _optimize_movie_use_case

    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500

    try:
        profiles = _optimize_movie_use_case.get_available_profiles()

        return jsonify(profiles)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/estimate', methods=['POST'])
def estimate_size():
    """Estima el tamaño de un video optimizado"""
    global _estimate_size_use_case

    if _estimate_size_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500

    try:
        data = request.get_json()

        file_path = data.get('file_path')
        profile = data.get('profile', 'balanced')

        if not file_path:
            return jsonify({'error': 'file_path es requerido'}), 400

        estimate = _estimate_size_use_case.execute(file_path, profile)

        if estimate:
            return jsonify(estimate)
        else:
            return jsonify({'error': 'No se pudo calcular la estimación'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
