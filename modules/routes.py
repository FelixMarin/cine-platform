import os
import re
import jwt
import unicodedata
import threading
import time
import queue
import json
import magic
import logging
from modules.ffmpeg import FFmpegHandler
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response, send_from_directory, make_response
from werkzeug.utils import secure_filename
from modules.worker import start_worker
from flask_wtf.csrf import generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configurar logger
logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov'}

def create_blueprints(auth_service, media_service, optimizer_service):
    limiter = Limiter(key_func=get_remote_address)
    bp = Blueprint('main', __name__)

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

    # Iniciar worker (pasa las referencias necesarias)
    start_worker(processing_queue, processing_status, optimizer_service)    

    # --- Helpers ---
    def is_logged_in():
        return session.get("logged_in") is True

    def is_admin():
        return session.get('user_role') == 'admin'

    def validate_folder_path(folder_path):
        """
        Valida que una ruta de carpeta sea segura y exista
        """
        if not folder_path or not isinstance(folder_path, str):
            return None
        
        # Normalizar ruta
        try:
            abs_path = os.path.abspath(folder_path)
            
            # Verificar que la ruta existe
            if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
                return None
            
            # Verificar que está dentro de un directorio permitido
            # Esto depende de tu configuración - aquí asumimos /data/media
            allowed_base = os.path.abspath(os.environ.get('MOVIES_FOLDER', '/data/media'))
            if not os.path.exists(allowed_base):
                logger.error(f"MOVIES_FOLDER no existe: {allowed_base}")
                return None

            if os.path.commonpath([abs_path, allowed_base]) != allowed_base:
                logger.warning(f"Intento de acceso a ruta no permitida: {folder_path}")
                return None
            
            return abs_path
        except Exception as e:
            logger.error(f"Error validando ruta: {e}")
            return None

    def clean_filename(filename):
        # Eliminar sufijos comunes
        name = re.sub(r'[-_]?optimized', '', filename, flags=re.IGNORECASE)
        
        # Eliminar extensión y reemplazar separadores
        name = re.sub(r'\.(mkv|mp4|avi|mov)$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[._-]', ' ', name)
        
        # Capitalizar palabras
        return ' '.join(word.capitalize() for word in name.split())

    # --- AUTH ---
    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            # Generar token CSRF y guardarlo en sesión
            token = generate_csrf()
            session['csrf_token'] = token
            # Pasar el token explícitamente al template
            return render_template("login.html", csrf_token=token)

        # POST request
        # Validar CSRF token
        csrf_token = request.form.get('csrf_token')
        session_token = session.get('csrf_token')
                
        # Si el token CSRF no es válido, generar uno nuevo y mostrar error
        if not csrf_token or not session_token or csrf_token != session_token:
            logger.warning("❌ Intento de CSRF detectado - tokens no coinciden")
            # Generar un NUEVO token para el formulario de error
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error="Token de seguridad inválido", csrf_token=new_token), 400

        # Limpiar el token de sesión después de usarlo (opcional)
        session.pop('csrf_token', None)

        username = request.form.get('email')
        password = request.form.get('password')

        if not username or not password:
            # Generar nuevo token para el formulario de error
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error="Usuario y contraseña requeridos", csrf_token=new_token), 400

        # Intentar login con el servicio OAuth
        success, info = auth_service.login(username, password)

        if not success:
            # Login fallido - generar nuevo token
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            logger.warning(f"❌ Login fallido para: {username}")
            return render_template("login.html", error="Credenciales incorrectas", csrf_token=new_token), 401

        # Login exitoso - procesar token JWT
        token = auth_service.token

        # Decodificar payload manualmente (debug)
        try:
            import base64
            import json
            parts = token.split('.')
            if len(parts) >= 2:
                payload_b64 = parts[1]
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload_json = base64.b64decode(payload_b64).decode('utf-8')
                payload = json.loads(payload_json)
                logger.warning(f"🔍 AUDIENCE EN EL TOKEN: {payload.get('aud')}")
                logger.warning(f"🔍 TODOS LOS CLAIMS: {list(payload.keys())}")
                logger.warning(f"🔍 PAYLOAD COMPLETO: {payload}")
        except Exception as e:
            logger.error(f"❌ Error decodificando payload: {e}")

        # ===== BLOQUE 1: Ver token sin verificar =====
        logger.info("🔍 ANALIZANDO TOKEN SIN VERIFICAR...")
        unverified = None
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            logger.info("✅ Token decodificado sin verificar:")
            logger.info(f"   - Algoritmo: {unverified.get('alg', 'N/A')}")
            logger.info(f"   - Claims: {list(unverified.keys())}")
            logger.info(f"   - aud: {unverified.get('aud')}")
            logger.info(f"   - iss: {unverified.get('iss')}")
            logger.info(f"   - sub: {unverified.get('sub')}")
            logger.info(f"   - exp: {unverified.get('exp')}")
            logger.info(f"   - authorities: {unverified.get('authorities')}")
            logger.info(f"   - user_name: {unverified.get('user_name')}")
        except Exception as e:
            logger.error(f"❌ Error decodificando token sin verificar: {type(e).__name__}: {e}")
            # Generar nuevo token para el formulario de error
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error=f"Token inválido: {type(e).__name__}", csrf_token=new_token), 400

        try:
            decoded = jwt.decode(
                token,
                key=os.environ.get('JWT_SECRET_KEY'),
                algorithms=['HS256'],
                audience=[os.environ.get('JWT_AUDIENCE')],
                options={"verify_signature": True}
            )
            logger.info("✅ Token verificado correctamente")

            # Establecer sesión de usuario
            session['logged_in'] = True
            session['user_email'] = decoded.get("user_name", username)
            session.permanent = True

            authorities = decoded.get("authorities", [])
            session['user_role'] = "admin" if "ROLE_ADMIN" in authorities else "user"

            logger.info(f"✅ Usuario autenticado: {session['user_email']} (rol: {session['user_role']})")

            return redirect(url_for('main.index'))

        except jwt.ExpiredSignatureError:
            logger.error("❌ Token expirado")
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error="Sesión expirada", csrf_token=new_token), 400
        except jwt.InvalidAudienceError as e:
            logger.error(f"❌ Audience incorrecto: {e}")
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error="Error de autenticación", csrf_token=new_token), 400
        except jwt.InvalidSignatureError:
            logger.error("❌ Firma incorrecta")
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error="Error de autenticación", csrf_token=new_token), 400
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Token inválido: {type(e).__name__}: {e}")
            new_token = generate_csrf()
            session['csrf_token'] = new_token
            return render_template("login.html", error="Error de autenticación", csrf_token=new_token), 400

    @bp.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('main.login'))

    # --- STREAMING ---
    @bp.route('/')
    def index():
        if not is_logged_in():
            return redirect(url_for('main.login'))
        movies, series = media_service.list_content()
        return render_template("index.html", movies=movies, series=series)

    @bp.route('/play/<path:filename>')
    def play(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))
        
        # Validación robusta de path traversal
        if not media_service.is_path_safe(filename):
            logger.warning(f"Intento de path traversal en play: {repr(filename)}")
            return "Nombre de archivo inválido", 400
        
        # Verificar que el archivo existe
        file_path = media_service.get_safe_path(filename)
        if not file_path:
            return "Archivo no encontrado", 404
        
        # Usar el nombre base y limpiarlo para mostrar (título)
        base_name = os.path.basename(filename)
        display_name = clean_filename(base_name)
        
        # Pasar el filename ORIGINAL (con ruta completa) al template
        return render_template("play.html", filename=filename, sanitized_name=display_name)

    @bp.route('/stream/<path:filename>')
    def stream_video(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))

        # Usar get_safe_path que ya valida path traversal
        file_path = media_service.get_safe_path(filename)
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"Archivo no encontrado o acceso no autorizado: {filename}")
            return "Archivo no encontrado", 404

        file_size = os.path.getsize(file_path)
        range_header = request.headers.get('Range', None)

        if range_header:
            try:
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0])
                end = int(byte_range[1]) if byte_range[1] else file_size - 1
                
                # Validar rangos
                if start < 0 or end >= file_size or start > end:
                    return "Rango inválido", 416
            except (ValueError, IndexError):
                return "Rango inválido", 416
        else:
            start = 0
            end = file_size - 1

        length = end - start + 1

        def generate():
            try:
                with open(file_path, "rb") as video:
                    video.seek(start)
                    bytes_remaining = length
                    chunk_size = 1024 * 1024  # 1MB
                    
                    while bytes_remaining > 0:
                        chunk = video.read(min(chunk_size, bytes_remaining))
                        if not chunk:
                            break
                        yield chunk
                        bytes_remaining -= len(chunk)
            except Exception as e:
                logger.error(f"Error en streaming: {e}")

        content_type = "video/mp4" if filename.endswith(".mp4") else "video/x-matroska"

        response = Response(generate(), status=206, content_type=content_type)
        response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
        response.headers.add("Accept-Ranges", "bytes")
        response.headers.add("Content-Length", str(length))
        response.headers.add("X-Content-Type-Options", "nosniff")  # Seguridad
        return response

    @bp.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))
        
        # Validar filename para evitar path traversal
        if not media_service.is_path_safe(filename):
            logger.warning(f"Intento de path traversal en thumbnails: {filename}")
            return "Nombre de archivo inválido", 400
        
        thumbnails_folder = media_service.get_thumbnails_folder()
        accept_webp = 'image/webp' in request.headers.get('Accept', '')
        
        if filename.endswith('.jpg') and accept_webp:
            webp_filename = filename.replace('.jpg', '.webp')
            webp_path = os.path.join(thumbnails_folder, webp_filename)
            
            if os.path.exists(webp_path):
                response = make_response(send_from_directory(thumbnails_folder, webp_filename))
                response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
                response.headers['X-Image-Format'] = 'webp'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                return response
        
        response = make_response(send_from_directory(thumbnails_folder, filename))
        response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
        response.headers['X-Image-Format'] = 'jpg' if filename.endswith('.jpg') else 'webp'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response

    @bp.route('/thumbnails/detect/<filename>')
    def detect_thumbnail_format(filename):
        if not is_logged_in():
            return jsonify({"error": "No autorizado"}), 401
        
        # Validar filename
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"Intento de path traversal en detect: {filename}")
            return jsonify({"error": "Nombre de archivo inválido"}), 400
        
        thumbnails_folder = media_service.get_thumbnails_folder()
        base_name = os.path.splitext(filename)[0]
        
        jpg_path = os.path.join(thumbnails_folder, f"{base_name}.jpg")
        webp_path = os.path.join(thumbnails_folder, f"{base_name}.webp")
        
        return jsonify({
            "base_name": base_name,
            "has_jpg": os.path.exists(jpg_path),
            "has_webp": os.path.exists(webp_path),
            "jpg_url": f"/thumbnails/{base_name}.jpg" if os.path.exists(jpg_path) else None,
            "webp_url": f"/thumbnails/{base_name}.webp" if os.path.exists(webp_path) else None
        })

    @bp.route('/download/<path:filename>')
    def download_file(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))
        
        file_path = media_service.get_safe_path(filename)
        if not file_path:
            logger.warning(f"Intento de descarga no autorizada: {filename}")
            return "Archivo no encontrado", 404
        
        response = send_from_directory(
            os.path.dirname(file_path), 
            os.path.basename(file_path), 
            as_attachment=True
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    # --- OPTIMIZER ---
    @bp.route('/optimizer')
    def optimizer():
        if not is_logged_in():
            return redirect(url_for('main.login'))
        if not is_admin():
            return "Acceso denegado", 403
        return render_template("optimizer.html")

    @bp.route('/optimizer/profiles', methods=['GET'])
    def get_profiles():
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403
        
        try:
            if hasattr(optimizer_service, 'pipeline') and hasattr(optimizer_service.pipeline, 'get_profiles'):
                profiles = optimizer_service.pipeline.get_profiles()
            else:
                profiles = {
                    "ultra_fast": {
                        "name": "Ultra Rápido",
                        "description": "⚡ Máxima velocidad - Calidad baja",
                        "preset": "ultrafast",
                        "crf": 28,
                        "resolution": "480p"
                    },
                    "fast": {
                        "name": "Rápido",
                        "description": "🚀 Rápido - Calidad media-baja",
                        "preset": "veryfast",
                        "crf": 26,
                        "resolution": "540p"
                    },
                    "balanced": {
                        "name": "Balanceado",
                        "description": "⚖️ Balanceado - Buena calidad/velocidad",
                        "preset": "medium",
                        "crf": 23,
                        "resolution": "720p"
                    },
                    "high_quality": {
                        "name": "Alta Calidad",
                        "description": "🎯 Alta calidad - Más lento",
                        "preset": "slow",
                        "crf": 20,
                        "resolution": "1080p"
                    },
                    "master": {
                        "name": "Master",
                        "description": "💎 Calidad original - Muy lento",
                        "preset": "veryslow",
                        "crf": 18,
                        "resolution": "Original"
                    }
                }
            return jsonify(profiles)
        except Exception as e:
            logger.error(f"Error obteniendo perfiles: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/optimizer/estimate', methods=['POST'])
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
            
            # Validar filename
            safe_filename = secure_filename(filename)
            if not safe_filename:
                return jsonify({"error": "Nombre de archivo inválido"}), 400
            
            # Buscar el archivo en la carpeta de uploads
            filepath = os.path.join(optimizer_service.get_upload_folder(), safe_filename)
            
            # Si no existe en uploads, buscar en temp
            if not os.path.exists(filepath):
                temp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', safe_filename)
                if os.path.exists(temp_path):
                    filepath = temp_path
            
            if not os.path.exists(filepath):
                return jsonify({"error": "Archivo no encontrado"}), 404
            
            # Obtener tamaño real del archivo
            file_size = os.path.getsize(filepath)
            original_mb = file_size / (1024 * 1024)
            
            # Calcular estimación basada en el perfil
            ratios = {
                'ultra_fast': 0.15,
                'fast': 0.12,
                'balanced': 0.10,
                'high_quality': 0.25,
                'master': 0.50
            }
            
            ratio = ratios.get(profile, 0.10)
            estimated_mb = original_mb * ratio
            
            # Obtener duración (opcional)
            duration = 0
            try:
                from modules.ffmpeg import FFmpegHandler
                from modules.state import StateManager
                ff = FFmpegHandler(StateManager())
                duration = ff.get_duration(filepath)
            except:
                pass
            
            return jsonify({
                "original_mb": original_mb,
                "estimated_mb": estimated_mb,
                "compression_ratio": f"{int((1 - ratio) * 100)}%",
                "duration": duration,
                "filename": safe_filename
            })
            
        except Exception as e:
            logger.error(f"Error estimando: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route("/process-file", methods=["POST"])
    @limiter.limit("5 per minute")
    def process_file():
        """Endpoint para subir archivos - Responde inmediatamente"""
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403

        if "video" not in request.files:
            return jsonify({"error": "No file"}), 400

        video_file = request.files["video"]
        profile = request.form.get('profile', 'balanced')
        
        # Validar nombre de archivo
        if not video_file.filename:
            return jsonify({"error": "Nombre de archivo vacío"}), 400
            
        # Asegurar nombre seguro
        safe_filename = secure_filename(video_file.filename)
        if not safe_filename:
            return jsonify({"error": "Nombre de archivo inválido"}), 400
        
        # Validar extensión
        ext = os.path.splitext(safe_filename)[1].lower()
        if ext not in VIDEO_EXTENSIONS:
            return jsonify({"error": "Tipo de archivo no permitido"}), 400
        
        save_path = os.path.join(optimizer_service.get_upload_folder(), safe_filename)
        
        # Guardar archivo
        try:
            video_file.save(save_path)
            logger.info(f"✅ Archivo guardado: {save_path}")
        except Exception as e:
            logger.error(f"Error guardando archivo: {e}")
            return jsonify({"error": "Error guardando archivo"}), 500

        # Después de guardar temporalmente
        mime = magic.from_file(save_path, mime=True)
        if not mime.startswith('video/'):
            os.remove(save_path)
            return jsonify({"error": "El archivo no es un video válido"}), 400

        # Validar con ffprobe
        from modules.ffmpeg import FFmpegHandler
        ff = FFmpegHandler(StateManager())
        info = ff.get_video_info(save_path)
        if not info or info.get('vcodec') == 'desconocido':
            os.remove(save_path)
            return jsonify({"error": "Formato de video no válido"}), 400

        # Añadir a la cola de procesamiento
        processing_queue.put({
            'filepath': save_path,
            'filename': safe_filename,
            'profile': profile
        })
        
        # Responder inmediatamente
        return jsonify({
            "message": f"Archivo recibido: {safe_filename}",
            "status": "queued",
            "file": safe_filename,
            "profile": profile,
            "queue_position": processing_queue.qsize()
        }), 202

    @bp.route("/process-status", methods=["GET"])
    def process_status():
        """Devuelve el estado de la cola de procesamiento"""
        if not is_logged_in():
            return jsonify({"error": "No autorizado"}), 401
        
        return jsonify({
            "current": processing_status["current"],
            "queue_size": processing_queue.qsize(),
            "last_update": processing_status["last_update"]
        })

    @bp.route("/status")
    def status():
        """Devuelve el estado actual del procesamiento"""
        try:
            # Cargar historial desde state.json
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

    @bp.route("/process", methods=["POST"])
    def process_folder_route():
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON inválido"}), 400
            
        folder = data.get("folder")

        # Validar ruta de carpeta
        safe_folder = validate_folder_path(folder)
        if not safe_folder:
            logger.warning(f"Intento de procesar ruta no válida: {folder}")
            return jsonify({"error": "Ruta de carpeta no válida"}), 400

        optimizer_service.process_folder(safe_folder)
        return jsonify({"message": f"Procesando carpeta: {safe_folder}"}), 200

    @bp.route('/outputs/<filename>')
    def serve_output(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))
        
        # Validar filename
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"Intento de path traversal en outputs: {filename}")
            return "Nombre de archivo inválido", 400
            
        return send_from_directory(optimizer_service.get_output_folder(), filename)

    # --- ADMIN ---
    @bp.route('/admin/manage')
    def admin_manage():
        if not is_logged_in():
            return redirect(url_for('main.login'))  # Redirect a login si no está autenticado
        
        if not is_admin():
            return render_template("403.html"), 403  # Template de acceso denegado
        
        return render_template("admin_panel.html")

    # --- API: Películas y Series ---
    @bp.route('/api/movies')
    def api_movies():
        if not is_logged_in():
            return jsonify({"error": "No autorizado"}), 401

        categorias, series = media_service.list_content()
        
        def normalize_dict(d):
            if isinstance(d, dict):
                return {unicodedata.normalize('NFC', k): normalize_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [normalize_dict(item) for item in d]
            elif isinstance(d, str):
                return unicodedata.normalize('NFC', d)
            else:
                return d
        
        categorias = normalize_dict(categorias)
        series = normalize_dict(series)

        response = jsonify({"categorias": categorias, "series": series})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    @bp.route('/api/thumbnail-status')
    def thumbnail_status():
        if not is_logged_in():
            return jsonify({"error": "No autorizado"}), 401
        
        status = media_service.get_thumbnail_status()
        status["timestamp"] = time.time()
        
        response = jsonify(status)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Cache-Control'] = 'no-cache'
        return response

    @bp.route('/cancel-process', methods=['POST'])
    def cancel_process():
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403
        
        try:
            processing_status["cancelled"] = True
            logger.info("Proceso cancelado por usuario")
            return jsonify({"message": "Cancelando proceso..."}), 200
            
        except Exception as e:
            logger.error(f"Error cancelando proceso: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.after_request
    def add_security_headers(response):
        """Añadir headers de seguridad a todas las respuestas"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if response.content_type == 'application/json':
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        
        return response

    return bp