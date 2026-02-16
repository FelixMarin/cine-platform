import os
import jwt
import unicodedata
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response, send_from_directory

def create_blueprints(auth_service, media_service, optimizer_service):
    bp = Blueprint('main', __name__)

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

                # Decodificar JWT sin verificar firma
                decoded = jwt.decode(token, options={"verify_signature": False})

                # Guardar solo lo necesario en la sesión (NO el JWT)
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
        """
        Sirve thumbnails con soporte para WebP y cabeceras de caché
        """
        if not is_logged_in():
            return redirect(url_for('main.login'))
        
        thumbnails_folder = media_service.get_thumbnails_folder()
        
        # Verificar si el navegador acepta WebP
        accept_webp = 'image/webp' in request.headers.get('Accept', '')
        
        # Si el archivo solicitado es .jpg pero el navegador acepta WebP,
        # intentar servir la versión WebP si existe
        if filename.endswith('.jpg') and accept_webp:
            webp_filename = filename.replace('.jpg', '.webp')
            webp_path = os.path.join(thumbnails_folder, webp_filename)
            
            if os.path.exists(webp_path):
                response = make_response(send_from_directory(thumbnails_folder, webp_filename))
                response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
                response.headers['X-Image-Format'] = 'webp'
                return response
        
        # Servir el archivo solicitado
        response = make_response(send_from_directory(thumbnails_folder, filename))
        response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
        response.headers['X-Image-Format'] = 'jpg' if filename.endswith('.jpg') else 'webp'
        
        return response

    @bp.route('/thumbnails/detect/<filename>')
    def detect_thumbnail_format(filename):
        """
        Endpoint para detectar qué formatos de thumbnail existen
        """
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

    @bp.route("/process-file", methods=["POST"])
    def process_file():
        if not is_logged_in() or not is_admin():
            return jsonify({"error": "No autorizado"}), 403

        if "video" not in request.files:
            return jsonify({"error": "No file"}), 400

        video_file = request.files["video"]
        save_path = os.path.join(optimizer_service.get_upload_folder(), video_file.filename)
        video_file.save(save_path)

        optimizer_service.process_file(save_path)
        return jsonify({"message": f"Procesando: {video_file.filename}"})

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

    @bp.route("/status")
    def status():
        return jsonify(optimizer_service.get_status())

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
        
        # Normalizar todas las claves y valores a NFC
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

        response = jsonify({
            "categorias": categorias,
            "series": series
        })
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        
        return response

    # --- After request handler para UTF-8 en todas las respuestas JSON ---
    @bp.after_request
    def add_charset(response):
        """Añade charset UTF-8 a todas las respuestas JSON"""
        if response.content_type == 'application/json':
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    # --- IMPORTANTE: Devolver el blueprint ---
    return bp