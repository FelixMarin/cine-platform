import os
import jwt
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
        return send_from_directory(media_service.get_thumbnails_folder(), filename)

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

    return bp
