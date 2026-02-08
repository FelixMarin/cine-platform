from flask import Flask, Response, request, send_from_directory, render_template, redirect, url_for, session, jsonify
import os
import subprocess
import threading
import shutil
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from pb_client import PocketBaseClient
from modules.logging.logging_config import setup_logging

# Cargar variables de entorno desde .env
load_dotenv()

# Logging
logger = setup_logging("cine-platform")

app = Flask(__name__, template_folder="./templates", static_folder="./static", static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_me")

# --- SECURITY CONFIGURATION ---
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # Límite de subida: 16GB
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Previene acceso a cookie por JS (XSS mitigation)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Mitigación básica de CSRF

pb = PocketBaseClient(base_url=os.getenv("POCKETBASE_URL", "http://127.0.0.1:8070"))

def is_logged_in():
    return "pb_token" in session

# ============================================================================
# MOVIE STREAMING CONFIGURATION (from cinetix)
# ============================================================================

MOVIES_FOLDER = os.getenv("MOVIES_FOLDER", r"/media/d/audiovisual")
THUMBNAILS_FOLDER = os.path.join(MOVIES_FOLDER, "thumbnails")

# Crear la carpeta de miniaturas si no existe
if not os.path.exists(THUMBNAILS_FOLDER):
    os.makedirs(THUMBNAILS_FOLDER)

def validate_safe_path(base_dir, filename):
    """
    Valida que la ruta solicitada esté realmente dentro del directorio base
    para prevenir ataques de Path Traversal (ej: ../../etc/passwd).
    """
    base_dir = os.path.abspath(base_dir)
    # Unir y resolver la ruta absoluta
    target_path = os.path.abspath(os.path.join(base_dir, filename))
    
    # Verificar que la ruta resultante comience con el directorio base
    if not target_path.startswith(base_dir):
        logger.warning(f"ALERTA DE SEGURIDAD: Intento de Path Traversal detectado: {filename}")
        return None
    return target_path

def generate_thumbnail(video_path, thumbnail_path):
    """Genera una miniatura para un archivo de video usando FFmpeg."""
    try:
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-ss", "00:00:10", "-vframes", "1",
            "-vf", "scale=320:-1",
            thumbnail_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al generar miniatura para {video_path}: {e}")

def clean_filename(filename):
    """Limpia el nombre del archivo eliminando sufijos redundantes y ajustando el formato."""
    name = os.path.splitext(filename)[0]  # Quitar la extensión
    name = name.replace("-optimized", "").replace("_optimized", "").replace("-serie", "")  # Quitar sufijos
    name = name.replace("-", " ").replace("_", " ").replace(".", " ")  # Reemplazar separadores por espacios
    return name.title()  # Capitalizar palabras

def list_movies_and_series(folder):
    """Clasifica los archivos en películas y series."""
    movies = []
    series = {}

    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(('.mkv')):
                relative_path = os.path.relpath(os.path.join(root, file), MOVIES_FOLDER).replace("\\", "/")
                thumbnail_path = os.path.join(THUMBNAILS_FOLDER, f"{os.path.splitext(file)[0]}.jpg")

                # Genera miniatura si no existe
                if not os.path.exists(thumbnail_path):
                    generate_thumbnail(os.path.join(root, file), thumbnail_path)

                item = {
                    "name": clean_filename(file),
                    "path": relative_path,
                    "thumbnail": f"/thumbnails/{os.path.basename(thumbnail_path)}"
                }

                # Clasificar como serie o película
                if "-serie" in file.lower():
                    series_name = item["name"].rsplit(" T", 1)[0]
                    if series_name not in series:
                        series[series_name] = []
                    series[series_name].append(item)
                else:
                    movies.append(item)

    # Ordenar series y episodios en orden alfabético
    series = {k: sorted(v, key=lambda x: x["name"]) for k, v in sorted(series.items())}
    movies.sort(key=lambda x: x["name"])

    logger.info(f"Escaneo de medios completado: {len(movies)} películas, {len(series)} series.")
    logger.debug(f"Películas: {movies}, Series: {series}")

    return movies, series

# ============================================================================
# VIDEO OPTIMIZER CONFIGURATION (from video-optimizer)
# ============================================================================

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
TEMP_FOLDER = os.path.join(os.getcwd(), "temp")
OUTPUT_FOLDER = os.path.join(os.getcwd(), "outputs")

for folder in [UPLOAD_FOLDER, TEMP_FOLDER, OUTPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Variables globales para el estado del optimizador
current_video = None
current_step = 0
history = []
log_line = ""
video_info = {}
STATE_FILE = "state.json"

def save_state():
    """Guarda el estado actual en un archivo JSON."""
    try:
        state = {
            "current_video": current_video,
            "current_step": current_step,
            "history": history,
            "video_info": video_info
        }
        import json
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Error al guardar el estado: {e}")

def load_state():
    """Carga el estado desde el archivo JSON si existe."""
    global current_video, current_step, history, video_info
    if os.path.exists(STATE_FILE):
        try:
            import json
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                current_video = state.get("current_video")
                current_step = state.get("current_step", 0)
                history = state.get("history", [])
                video_info = state.get("video_info", {})
            logger.info("Estado cargado correctamente desde state.json")
        except Exception as e:
            logger.error(f"Error al cargar el estado: {e}")

# Cargar estado al iniciar
load_state()

# Extensiones válidas de vídeo
valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

def get_gpu_decoder():
    logger.debug("Detectando decoder GPU...")
    if os.path.exists("/usr/lib/aarch64-linux-gnu/tegra"):
        logger.info("Jetson detectada: usando h264_nvv4l2dec para decodificación")
        return "h264_nvv4l2dec"
    return None

def get_gpu_encoder():
    logger.debug("Detectando encoder GPU...")
    if os.path.exists("/usr/lib/aarch64-linux-gnu/tegra"):
        logger.info("Jetson Orin Nano detectada (sin NVENC): usando libx264 para codificación")
        return "libx264"
    logger.info("Jetson no detectada: usando libx264 (CPU)")
    return "libx264"

def run_ffmpeg_command(cmd):
    """Ejecuta un comando de FFmpeg y captura el progreso en tiempo real."""
    global log_line
    logger.debug(f"Ejecutando comando: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    for line in process.stdout:
        if "frame=" in line or "time=" in line:
            clean_line = " ".join(line.split())
            clean_line = clean_line.replace("= ", "=")
            
            parts = []
            for item in clean_line.split():
                if "=" in item:
                    k, v = item.split("=", 1)
                    if k == "frame": k = "frames"
                    parts.append(f"{k}={v}")
            
            log_line = " | ".join(parts)

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)
    
    log_line = ""

def process_video(video_path):
    global current_video, current_step, history, video_info
    start_time = time.time()

    # Ignorar archivos que ya tienen el sufijo "-optimized"
    if "-optimized" in video_path:
        return

    video_filename = os.path.basename(video_path)
    logger.info(f"--- Iniciando procesamiento de video: {video_filename} ---")
    current_video = video_filename
    save_state()

    # Asegurar que video_info esté poblado
    if not video_info or video_info.get("name") != video_filename:
        video_info = get_video_info(video_path)
        save_state()

    # Rutas en carpeta temporal
    temp_original_path = os.path.join(TEMP_FOLDER, video_filename)
    repaired_path = os.path.join(TEMP_FOLDER, video_filename.rsplit('.', 1)[0] + "_repaired.mkv")
    reduced_path = os.path.join(TEMP_FOLDER, video_filename.rsplit('.', 1)[0] + "_reduced.mkv")
    optimized_filename = video_filename.rsplit('.', 1)[0] + "-optimized.mkv"
    temp_optimized_path = os.path.join(TEMP_FOLDER, optimized_filename)
    final_output_path = os.path.join(OUTPUT_FOLDER, optimized_filename)

    try:
        # Paso 0: Copiar a temp
        logger.info(f"Copiando {video_filename} a la carpeta temporal")
        shutil.copy2(video_path, temp_original_path)

        # Paso 1: Reparar archivo
        current_step = 1
        save_state()
        logger.info(f"Paso {current_step}: Reparando archivo {current_video}")
        run_ffmpeg_command(["ffmpeg", "-y", "-i", temp_original_path, "-c", "copy", repaired_path])

        # Paso 2: Reducir tamaño
        current_step = 2
        save_state()
        logger.info(f"Paso {current_step}: Reduciendo tamaño de {current_video}")
        decoder = get_gpu_decoder()
        
        cmd_reducir = ["ffmpeg", "-y"]
        if decoder:
            cmd_reducir.extend(["-c:v", decoder])
            
        cmd_reducir.extend([
            "-i", repaired_path, 
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "2M", "-vf", "scale=1280:720", "-c:a", "aac", reduced_path
        ])
        
        logger.debug(f"Ejecutando FFmpeg para reducir tamaño: {' '.join(cmd_reducir)}")
        run_ffmpeg_command(cmd_reducir)

        # Paso 3: Optimizar para streaming
        current_step = 3
        save_state()
        logger.info(f"Paso {current_step}: Optimizando video {current_video} para streaming")
        decoder = get_gpu_decoder()
        encoder = get_gpu_encoder()
        
        cmd = ["ffmpeg", "-y"]
        if decoder:
            cmd.extend(["-c:v", decoder])
            
        cmd.extend(["-i", reduced_path, "-c:v", encoder])
        
        if encoder == "libx264":
            cmd.extend(["-preset", "slow", "-crf", "23", "-b:v", "1000k"])
        elif encoder == "h264_nvenc":
            cmd.extend(["-preset", "fast", "-cq", "23", "-b:v", "1000k"])
        else:
            cmd.extend(["-b:v", "1000k"])
            
        cmd.extend([
            "-r", "30", "-vf", "scale=1280:720",
            "-c:a", "aac", "-movflags", "faststart", temp_optimized_path
        ])
        
        logger.debug(f"Ejecutando comando de optimización: {' '.join(cmd)}")
        run_ffmpeg_command(cmd)

        # Paso 4: Validar duración
        current_step = 4
        save_state()
        logger.info(f"Paso {current_step}: Validando duración de {current_video}")
        original_duration = get_video_duration(temp_original_path)
        optimized_duration = get_video_duration(temp_optimized_path)
        logger.debug(f"Duración Original: {original_duration}s, Duración Optimizada: {optimized_duration}s")

        if abs(original_duration - optimized_duration) > 2:
            logger.error(f"Fallo en la validación de duración para {current_video}")
            raise ValueError("La duración del archivo optimizado no coincide con el original")

        # Paso 5: Mover a outputs
        logger.info(f"Moviendo resultado final a {final_output_path}")
        shutil.move(temp_optimized_path, final_output_path)

        # Eliminar archivos intermedios
        logger.info(f"Limpiando archivos temporales para {current_video}")
        for p in [temp_original_path, repaired_path, reduced_path]:
            if os.path.exists(p):
                os.remove(p)

        # Actualizar historial con éxito
        logger.info(f"+++ Video {current_video} procesado con éxito +++")
        finish_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        proc_duration = f"{round(time.time() - start_time, 1)}s"
        history.append({
            "name": current_video, 
            "status": "Procesado correctamente",
            "timestamp": finish_time,
            "duration": proc_duration
        })
        save_state()
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.exception(f"Error procesando el video {current_video}")
        finish_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        proc_duration = f"{round(time.time() - start_time, 1)}s"
        history.append({
            "name": current_video, 
            "status": f"Error: {str(e)}",
            "timestamp": finish_time,
            "duration": proc_duration
        })
        save_state()
    finally:
        current_video = None
        current_step = 0
        video_info = {}
        save_state()

def get_video_duration(video_path):
    """Devuelve la duración del video en segundos."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError:
        return 0.0

def get_video_info(video_path):
    """Obtiene información detallada del video usando ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)
        
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
        
        size_bytes = int(format_info.get("size", 0))
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        return {
            "name": os.path.basename(video_path),
            "duration": format_info.get("duration", "0"),
            "resolution": f"{v_stream.get('width', '??')}x{v_stream.get('height', '??')}",
            "format": format_info.get("format_name", "desconocido"),
            "vcodec": v_stream.get("codec_name", "desconocido"),
            "acodec": a_stream.get("codec_name", "desconocido"),
            "size": f"{size_mb} MB"
        }
    except Exception as e:
        logger.error(f"Error al obtener info del video: {e}")
        return {}

def process_folder(folder_path):
    global history
    history = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if os.path.splitext(file)[1].lower() in valid_extensions:
                video_path = os.path.join(root, file)
                process_video(video_path)

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, info = pb.login(email, password)
        if success:
            session['pb_token'] = pb.token
            session['user_email'] = info['email']
            session['user_role'] = info.get('role', 'user')
            logger.info(f"Login exitoso: {email}")
            return redirect(url_for('index'))
        else:
            logger.warning(f"Login fallido para: {email}")
            return render_template("login.html", error="Credenciales incorrectas")
    
    return render_template("login.html")

@app.route('/logout')
def logout():
    logger.info(f"Cerrando sesión: {session.get('user_email')}")
    session.clear()
    return redirect(url_for('login'))

# ============================================================================
# MOVIE STREAMING ROUTES
# ============================================================================

@app.route('/')
def index():
    """Página principal con lista de películas y series."""
    if not is_logged_in():
        return redirect(url_for('login'))

    logger.info(f"Cargando índice para usuario: {session.get('user_email')}")
    movies, series = list_movies_and_series(MOVIES_FOLDER)
    return render_template("index.html", movies=movies, series=series)

@app.route('/play/<path:filename>')
def play(filename):
    """Ruta para manejar reproducción de archivos."""
    if not is_logged_in():
        return redirect(url_for('login'))

    logger.info(f"Iniciando reproducción: {filename} (Usuario: {session.get('user_email')})")
    sanitized_name = clean_filename(os.path.basename(filename))
    return render_template("play.html", filename=filename, sanitized_name=sanitized_name)

@app.route('/stream/<path:filename>')
def stream_video(filename):
    """Ruta para hacer streaming del video."""
    if not is_logged_in():
        return redirect(url_for('login'))

    # Validación de seguridad para evitar Path Traversal
    file_path = validate_safe_path(MOVIES_FOLDER, filename)
    if not file_path or not os.path.exists(file_path):
        logger.error(f"Error streaming: Archivo no válido o no encontrado {filename}")
        return f"<h1>Error: Archivo no encontrado: {file_path}</h1>", 404

    file_size = os.path.getsize(file_path)

    # Manejo del encabezado Range para streaming
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

    # Determina el tipo MIME
    if filename.endswith(".mp4"):
        content_type = "video/mp4"
    elif filename.endswith(".mkv"):
        content_type = "video/x-matroska"
    elif filename.endswith(".avi"):
        content_type = "video/x-msvideo"
    else:
        content_type = "application/octet-stream"

    response = Response(generate(), status=206, content_type=content_type)
    response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    return response

@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Sirve las miniaturas generadas."""
    return send_from_directory(THUMBNAILS_FOLDER, filename)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Ruta para descargar un archivo."""
    if not is_logged_in():
        return redirect(url_for('login'))

    # Validación de seguridad para evitar Path Traversal
    file_path = validate_safe_path(MOVIES_FOLDER, filename)
    if not file_path or not os.path.exists(file_path):
        logger.error(f"Error descarga: Archivo no válido o no encontrado {filename}")
        return f"<h1>Error: Archivo no encontrado: {file_path}</h1>", 404
    logger.info(f"Descarga iniciada: {filename} (Usuario: {session.get('user_email')})")
    return send_from_directory(MOVIES_FOLDER, filename, as_attachment=True)

# ============================================================================
# VIDEO OPTIMIZER ROUTES
# ============================================================================

@app.route('/optimizer')
def optimizer():
    """Página del optimizador de videos."""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if session.get('user_role') != 'admin':
        logger.warning(f"Acceso denegado al optimizador. Usuario: {session.get('user_email')}")
        return "Acceso denegado: Se requieren permisos de administrador", 403
    
    logger.info(f"Acceso al optimizador: {session.get('user_email')}")
    return render_template("optimizer.html")

@app.route("/process-file", methods=["POST"])
def process_file():
    if not is_logged_in():
        return jsonify({"error": "No autenticado"}), 401
    
    if session.get('user_role') != 'admin':
        logger.warning(f"Acceso denegado a process-file. Usuario: {session.get('user_email')}")
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
        
    logger.info("Recibida petición de subida de archivo (/process-file)")
    if "video" not in request.files:
        logger.warning("Intento de subida sin archivo 'video'")
        return jsonify({"error": "No se envió archivo"}), 400

    video_file = request.files["video"]
    logger.info(f"Subiendo archivo: {video_file.filename}")

    save_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
    video_file.save(save_path)
    logger.debug(f"Archivo guardado en {save_path}")

    # Extraer info para el dashboard
    global video_info
    video_info = get_video_info(save_path)
    save_state()

    # Iniciar procesamiento en un hilo separado
    logger.info(f"Iniciando hilo de procesamiento para {video_file.filename}")
    threading.Thread(target=process_video, args=(save_path,)).start()

    return jsonify({"message": f"Procesamiento iniciado para: {video_file.filename}"}), 200

@app.route("/process", methods=["POST"])
def process():
    if not is_logged_in():
        return jsonify({"error": "No autenticado"}), 401
    
    if session.get('user_role') != 'admin':
        logger.warning(f"Acceso denegado a process. Usuario: {session.get('user_email')}")
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
        
    logger.info("Recibida petición de procesamiento por ruta (/process)")
    data = request.get_json()
    if not data or "folder" not in data:
        logger.warning("Petición /process sin 'folder' en el JSON")
        return jsonify({"error": "Ruta de carpeta no proporcionada"}), 400

    folder_path = data["folder"]
    logger.info(f"Ruta proporcionada: {folder_path}")
    if not os.path.exists(folder_path):
        logger.error(f"La ruta especificada no existe: {folder_path}")
        return jsonify({"error": "La ruta especificada no existe"}), 400

    # Procesar carpeta en un hilo separado
    logger.info(f"Iniciando hilo de procesamiento de carpeta: {folder_path}")
    threading.Thread(target=process_folder, args=(folder_path,)).start()

    return jsonify({"message": f"Procesando carpeta: {folder_path}"}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "current_video": current_video,
        "current_step": current_step,
        "history": history,
        "log_line": log_line,
        "video_info": video_info
    })

@app.route('/outputs/<filename>')
def serve_output(filename):
    """Sirve los videos optimizados."""
    if not is_logged_in():
        return redirect(url_for('login'))
    return send_from_directory(OUTPUT_FOLDER, filename)

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin/manage')
def admin_manage():
    if not is_logged_in() or session.get('user_role') != 'admin':
        logger.warning(f"Acceso denegado a admin panel. Usuario: {session.get('user_email')}")
        return "Acceso denegado: Se requieren permisos de administrador", 403
    
    logger.info(f"Acceso a admin panel autorizado: {session.get('user_email')}")
    return render_template("admin_panel.html")

# --- SECURITY HEADERS ---
@app.after_request
def set_security_headers(response):
    """Añade cabeceras de seguridad a todas las respuestas."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    logger.info(f"=== Iniciando Cine Platform en {host}:{port} ===")
    app.run(host=host, port=port, debug=False) # Debug desactivado para producción
