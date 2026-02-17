import os
import jwt
import unicodedata
import threading
import time
import queue
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response, send_from_directory, make_response
from werkzeug.utils import secure_filename
from modules.worker import start_worker

def create_blueprints(auth_service, media_service, optimizer_service):
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

    # --- AUTH ---
    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('email')
            password = request.form.get('password')

            success, info = auth_service.login(username, password)

            if success:
                token = auth_service.token
                decoded = jwt.decode(token, options={"verify_signature": False})

                session['logged_in'] = True
                session['user_email'] = decoded.get("user_name", username)

                authorities = decoded.get("authorities", [])
                session['user_role'] = "admin" if "ROLE_ADMIN" in authorities else "user"

                return redirect(url_for('main.index'))

            return render_template("login.html", error="Credenciales incorrectas")

        return render_template("login.html")

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
        sanitized_name = os.path.basename(filename).replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title()
        return render_template("play.html", filename=filename, sanitized_name=sanitized_name)

    @bp.route('/stream/<path:filename>')
    def stream_video(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))

        file_path = media_service.get_safe_path(filename)
        if not file_path or not os.path.exists(file_path):
            return "Archivo no encontrado", 404

        file_size = os.path.getsize(file_path)
        range_header = request.headers.get('Range', None)

        if range_header:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
        else:
            start = 0
            end = file_size - 1

        length = end - start + 1

        def generate():
            with open(file_path, "rb") as video:
                video.seek(start)
                while chunk := video.read(1024 * 1024):
                    yield chunk

        content_type = "video/mp4" if filename.endswith(".mp4") else "video/x-matroska"

        response = Response(generate(), status=206, content_type=content_type)
        response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
        response.headers.add("Accept-Ranges", "bytes")
        response.headers.add("Content-Length", str(length))
        return response

    @bp.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))
        
        thumbnails_folder = media_service.get_thumbnails_folder()
        accept_webp = 'image/webp' in request.headers.get('Accept', '')
        
        if filename.endswith('.jpg') and accept_webp:
            webp_filename = filename.replace('.jpg', '.webp')
            webp_path = os.path.join(thumbnails_folder, webp_filename)
            
            if os.path.exists(webp_path):
                response = make_response(send_from_directory(thumbnails_folder, webp_filename))
                response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
                response.headers['X-Image-Format'] = 'webp'
                return response
        
        response = make_response(send_from_directory(thumbnails_folder, filename))
        response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
        response.headers['X-Image-Format'] = 'jpg' if filename.endswith('.jpg') else 'webp'
        
        return response

    @bp.route('/thumbnails/detect/<filename>')
    def detect_thumbnail_format(filename):
        if not is_logged_in():
            return jsonify({"error": "No autorizado"}), 401
        
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
            return "Error", 404
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), as_attachment=True)

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
            print(f"Error obteniendo perfiles: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/optimizer/estimate', methods=['POST'])
    def estimate_optimization():
        """Estima el tamaño según perfil"""
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403
        
        try:
            data = request.get_json()
            filename = data.get('filepath')  # Esto es solo el nombre, no la ruta completa
            profile = data.get('profile', 'balanced')
            
            if not filename:
                return jsonify({"error": "filepath requerido"}), 400
            
            # Buscar el archivo en la carpeta de uploads
            filepath = os.path.join(optimizer_service.get_upload_folder(), filename)
            
            # Si no existe en uploads, buscar en temp
            if not os.path.exists(filepath):
                temp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', filename)
                if os.path.exists(temp_path):
                    filepath = temp_path
            
            if not os.path.exists(filepath):
                return jsonify({"error": "Archivo no encontrado"}), 404
            
            # Obtener tamaño real del archivo
            file_size = os.path.getsize(filepath)
            original_mb = file_size / (1024 * 1024)
            
            # Calcular estimación basada en el perfil
            ratios = {
                'ultra_fast': 0.15,  # 15% del original
                'fast': 0.12,         # 12% del original
                'balanced': 0.10,      # 10% del original
                'high_quality': 0.25,  # 25% del original
                'master': 0.50         # 50% del original
            }
            
            ratio = ratios.get(profile, 0.10)
            estimated_mb = original_mb * ratio
            
            # Obtener duración (opcional, para cálculos más precisos)
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
                "filename": filename
            })
            
        except Exception as e:
            print(f"Error estimando: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route("/process-file", methods=["POST"])
    def process_file():
        """Endpoint para subir archivos - Responde inmediatamente"""
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403

        if "video" not in request.files:
            return jsonify({"error": "No file"}), 400

        video_file = request.files["video"]
        profile = request.form.get('profile', 'balanced')
        
        # Asegurar nombre seguro
        safe_filename = secure_filename(video_file.filename)
        save_path = os.path.join(optimizer_service.get_upload_folder(), safe_filename)
        
        # Guardar archivo
        video_file.save(save_path)
        print(f"✅ Archivo guardado: {save_path}")
        
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
                print(f"Error cargando historial: {e}")
            
            # Devolver nuestro estado global incluyendo video_info
            return jsonify({
                "current_video": processing_status["current"],
                "log_line": processing_status["log_line"],
                "frames": processing_status["frames"],
                "fps": processing_status["fps"],
                "time": processing_status["time"],
                "speed": processing_status["speed"],
                "queue_size": processing_queue.qsize(),
                "video_info": processing_status.get("video_info", {}),
                "history": history  # <-- AHORA INCLUYE EL HISTORIAL
            })
        except Exception as e:
            print(f"Error en /status: {e}")
            return jsonify({
                "current_video": processing_status.get("current"),
                "log_line": f"Error: {str(e)}",
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
        folder = data.get("folder")

        if not folder or not os.path.exists(folder):
            return jsonify({"error": "Ruta inválida"}), 400

        optimizer_service.process_folder(folder)
        return jsonify({"message": f"Procesando carpeta: {folder}"})

    @bp.route('/outputs/<filename>')
    def serve_output(filename):
        if not is_logged_in():
            return redirect(url_for('main.login'))
        return send_from_directory(optimizer_service.get_output_folder(), filename)

    # --- ADMIN ---
    @bp.route('/admin/manage')
    def admin_manage():
        if not is_logged_in() or not is_admin():
            return "Acceso denegado", 403
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
            # Marcar cancelación
            processing_status["cancelled"] = True
            
            return jsonify({"message": "Cancelando proceso..."}), 200
            
        except Exception as e:
            print(f"Error cancelando proceso: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.after_request
    def add_charset(response):
        if response.content_type == 'application/json':
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    return bp