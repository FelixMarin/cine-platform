# modules/routes/optimizer.py
"""
Blueprint de optimizer: /optimizer, /process, /process-file, /process-status, /status, /cancel-process
"""
import os
import re
import time
import queue
import json
from flask import Blueprint, render_template, request, session, jsonify
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

optimizer_bp = Blueprint('optimizer', __name__)

# Servicios inyectados desde fuera
optimizer_service = None
media_service = None

# Configuración de rate limiting
limiter = Limiter(key_func=get_remote_address)

# Cola de procesamiento global
processing_queue = queue.Queue()
processing_status = {
    "current": None,
    "queue_size": 0,
    "log_line": "",
    "frames": 0,
    "fps": 0,
    "time": "",
    "speed": "",
    "video_info": {},
    "cancelled": False,
    "last_update": time.time()
}

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov'}


def init_services(optimizer_svc, media_svc, worker_queue, worker_status):
    """Inicializa los servicios"""
    global optimizer_service, media_service, processing_queue, processing_status
    optimizer_service = optimizer_svc
    media_service = media_svc
    processing_queue = worker_queue
    processing_status = worker_status


# Asignar como método del blueprint para permitir llamada directa
optimizer_bp.init_services = staticmethod(init_services)


def is_logged_in():
    return session.get("logged_in") is True


def is_admin():
    return session.get('user_role') == 'admin'


def validate_folder_path(folder_path):
    """Valida que una ruta de carpeta sea segura y exista"""
    if not folder_path or not isinstance(folder_path, str):
        return None
    
    try:
        abs_path = os.path.abspath(folder_path)
        
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return None
        
        allowed_base = os.path.abspath(os.environ.get('MOVIES_FOLDER', '/data/media'))
        if not os.path.exists(allowed_base):
            logger.error(f"MOVIES_FOLDER no existe: {allowed_base}")
            return None

        if os.path.commonpath([abs_path, allowed_base]) != allowed_base:
            return None
        
        return abs_path
    except Exception as e:
        logger.error(f"Error validando ruta: {e}")
        return None


@optimizer_bp.route('/optimizer')
def optimizer():
    """Página principal del optimizador"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    if not is_admin():
        return "Acceso denegado", 403
    return render_template("optimizer.html")


@optimizer_bp.route('/optimizer/profiles', methods=['GET'])
def get_profiles():
    """Devuelve los perfiles de optimización disponibles"""
    if not is_logged_in() or not is_admin():
        return jsonify({"error": "No autorizado"}), 403
    
    try:
        if hasattr(optimizer_service, 'pipeline') and hasattr(optimizer_service.pipeline, 'get_profiles'):
            profiles = optimizer_service.pipeline.get_profiles()
        else:
            profiles = {
                "ultra_fast": {"name": "Ultra Rápido", "description": "⚡ Máxima velocidad - Calidad baja", "preset": "ultrafast", "crf": 28, "resolution": "480p"},
                "fast": {"name": "Rápido", "description": "🚀 Rápido - Calidad media-baja", "preset": "veryfast", "crf": 26, "resolution": "540p"},
                "balanced": {"name": "Balanceado", "description": "⚖️ Balanceado - Buena calidad/velocidad", "preset": "medium", "crf": 23, "resolution": "720p"},
                "high_quality": {"name": "Alta Calidad", "description": "🎯 Alta calidad - Más lento", "preset": "slow", "crf": 20, "resolution": "1080p"},
                "master": {"name": "Master", "description": "💎 Calidad original - Muy lento", "preset": "veryslow", "crf": 18, "resolution": "Original"}
            }
        return jsonify(profiles)
    except Exception as e:
        logger.error(f"Error obteniendo perfiles: {e}")
        return jsonify({"error": str(e)}), 500


@optimizer_bp.route('/optimizer/estimate', methods=['POST'])
def estimate_optimization():
    """Estima el tamaño según perfil"""
    if not is_logged_in() or not is_admin():
        return jsonify({"error": "No autorizado"}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON inválido"}), 400
            
        filename = data.get('filepath')
        profile = data.get('profile', 'balanced')
        
        if not filename:
            return jsonify({"error": "filepath requerido"}), 400
        
        safe_filename = secure_filename(filename)
        if not safe_filename:
            return jsonify({"error": "Nombre de archivo inválido"}), 400
        
        filepath = os.path.join(optimizer_service.get_upload_folder(), safe_filename)
        
        if not os.path.exists(filepath):
            temp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', safe_filename)
            if os.path.exists(temp_path):
                filepath = temp_path
        
        if not os.path.exists(filepath):
            return jsonify({"error": "Archivo no encontrado"}), 404
        
        file_size = os.path.getsize(filepath)
        original_mb = file_size / (1024 * 1024)
        
        ratios = {'ultra_fast': 0.15, 'fast': 0.12, 'balanced': 0.10, 'high_quality': 0.25, 'master': 0.50}
        ratio = ratios.get(profile, 0.10)
        estimated_mb = original_mb * ratio
        
        return jsonify({
            "original_mb": original_mb,
            "estimated_mb": estimated_mb,
            "compression_ratio": f"{int((1 - ratio) * 100)}%",
            "filename": safe_filename
        })
        
    except Exception as e:
        logger.error(f"Error estimando: {e}")
        return jsonify({"error": str(e)}), 500


@optimizer_bp.route("/process-file", methods=["POST"])
@limiter.limit("5 per minute")
def process_file():
    """Endpoint para subir archivos - Responde inmediatamente"""
    if not is_logged_in() or not is_admin():
        return jsonify({"error": "No autorizado"}), 403

    if "video" not in request.files:
        return jsonify({"error": "No file"}), 400

    video_file = request.files["video"]
    profile = request.form.get('profile', 'balanced')
    
    if not video_file.filename:
        return jsonify({"error": "Nombre de archivo vacío"}), 400
        
    safe_filename = secure_filename(video_file.filename)
    if not safe_filename:
        return jsonify({"error": "Nombre de archivo inválido"}), 400
    
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        return jsonify({"error": "Tipo de archivo no permitido"}), 400
    
    save_path = os.path.join(optimizer_service.get_upload_folder(), safe_filename)
    
    try:
        video_file.save(save_path)
        logger.info(f"✅ Archivo guardado: {save_path}")
    except Exception as e:
        logger.error(f"Error guardando archivo: {e}")
        return jsonify({"error": "Error guardando archivo"}), 500

    # Validar MIME type
    try:
        import magic
        mime = magic.from_file(save_path, mime=True)
        if not mime.startswith('video/'):
            os.remove(save_path)
            return jsonify({"error": "El archivo no es un video válido"}), 400
    except Exception as e:
        logger.error(f"Error validando MIME: {e}")
        os.remove(save_path)
        return jsonify({"error": "Error validando archivo"}), 500

    # Validar con ffprobe
    from modules.ffmpeg import FFmpegHandler
    from modules.state import StateManager
    ff = FFmpegHandler(StateManager())
    info = ff.get_video_info(save_path)
    if not info or info.get('vcodec') == 'desconocido':
        os.remove(save_path)
        return jsonify({"error": "Formato de video no válido"}), 400

    # REGISTRAR LA SUBIDA PARA NOVEDADES
    if media_service and hasattr(media_service, 'register_upload'):
        try:
            media_service.register_upload(save_path)
            logger.info(f"📝 Subida registrada para novedades: {safe_filename}")
        except Exception as e:
            logger.error(f"Error registrando subida: {e}")

    # Añadir a la cola de procesamiento
    processing_queue.put({
        'filepath': save_path,
        'filename': safe_filename,
        'profile': profile
    })
    
    # Invalidar caché del catálogo para que aparezca como novedad
    if media_service and hasattr(media_service, 'invalidate_cache'):
        try:
            media_service.invalidate_cache()
            logger.info("🗑️ Caché de catálogo invalidada")
        except Exception as e:
            logger.error(f"Error invalidando caché: {e}")
    
    return jsonify({
        "message": f"Archivo recibido: {safe_filename}",
        "status": "queued",
        "file": safe_filename,
        "profile": profile,
        "queue_position": processing_queue.qsize()
    }), 202


@optimizer_bp.route("/process-status", methods=["GET"])
def process_status():
    """Devuelve el estado de la cola de procesamiento"""
    if not is_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    
    return jsonify({
        "current": processing_status["current"],
        "queue_size": processing_queue.qsize(),
        "last_update": processing_status["last_update"]
    })


@optimizer_bp.route("/status")
def status():
    """Devuelve el estado actual del procesamiento"""
    try:
        history = []
        state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'state.json')
        
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    history = state_data.get('history', [])
        except Exception as e:
            logger.error(f"Error cargando historial: {e}")
        
        return jsonify({
            "current_video": processing_status["current"],
            "log_line": processing_status["log_line"],
            "frames": processing_status["frames"],
            "fps": processing_status["fps"],
            "time": processing_status["time"],
            "speed": processing_status["speed"],
            "queue_size": processing_queue.qsize(),
            "video_info": processing_status.get("video_info", {}),
            "history": history
        })
    except Exception as e:
        logger.error(f"Error en /status: {e}")
        return jsonify({
            "current_video": processing_status.get("current"),
            "log_line": "Error interno del servidor",
            "frames": 0,
            "fps": 0,
            "time": "",
            "speed": "",
            "queue_size": processing_queue.qsize(),
            "video_info": {},
            "history": []
        })


@optimizer_bp.route("/process", methods=["POST"])
def process_folder_route():
    """Procesa una carpeta de videos"""
    if not is_logged_in() or not is_admin():
        return jsonify({"error": "No autorizado"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON inválido"}), 400
        
    folder = data.get("folder")

    safe_folder = validate_folder_path(folder)
    if not safe_folder:
        return jsonify({"error": "Ruta de carpeta no válida"}), 400

    optimizer_service.process_folder(safe_folder)
    return jsonify({"message": f"Procesando carpeta: {safe_folder}"}), 200


@optimizer_bp.route('/cancel-process', methods=['POST'])
def cancel_process():
    """Cancela el proceso actual"""
    if not is_logged_in() or not is_admin():
        return jsonify({"error": "No autorizado"}), 403
    
    try:
        processing_status["cancelled"] = True
        logger.info("Proceso cancelado por usuario")
        return jsonify({"message": "Cancelando proceso..."}), 200
    except Exception as e:
        logger.error(f"Error cancelando proceso: {e}")
        return jsonify({"error": str(e)}), 500