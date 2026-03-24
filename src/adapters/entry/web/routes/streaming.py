"""
Rutas de Streaming - Reproducción de video
"""

from flask import Blueprint, send_file, request, Response, jsonify
import os
import mimetypes

streaming_bp = Blueprint("streaming", __name__, url_prefix="/api/streaming")

# Blueprint adicional para /stream/ (sin prefijo /api/)
stream_page_bp = Blueprint("stream_page", __name__)


@stream_page_bp.route("/stream/<path:filename>")
def stream_page_video(filename):
    """Stream de video en /stream/ (para compatibilidad con templates)"""
    return stream_video(filename)


def init_streaming_routes():
    """Inicializa las rutas de streaming"""
    pass


@streaming_bp.route("/<path:filename>")
def stream_video(filename):
    """Stream de video con soporte para Range requests"""
    import time
    import logging

    logger = logging.getLogger(__name__)

    start_total = time.time()
    logger.info(f"🎬 Streaming iniciado para: {filename}")

    # Obtener la ruta del archivo - probar múltiples configuraciones
    movies_folder = os.environ.get("MOVIES_FOLDER", "/mnt/DATA_2TB/audiovisual")

    # URL decode el filename
    import urllib.parse

    filename = urllib.parse.unquote(filename)
    logger.info(f"📄 filename decodificado: {filename}")

    # Verificar si es una ruta válida existente
    file_path = None

    # Optimizado: probar solo con el prefijo correcto de Docker
    # En producción Docker, MOVIES_FOLDER es /data/movies pero el archivo está en /mnt/...
    # Primero probar como ruta relativa a MOVIES_FOLDER
    test_path = os.path.join(movies_folder, filename)
    if os.path.exists(test_path):
        file_path = test_path
    # También probar con la ruta alternativa de Docker
    elif movies_folder != "/data/movies":
        alt_path = os.path.join("/data/movies", filename)
        if os.path.exists(alt_path):
            file_path = alt_path

    if not file_path:
        logger.error(f"❌ Archivo no encontrado: {filename}")
        return "File not found", 404

    logger.info(f"✅ Archivo encontrado: {file_path}")

    if not os.path.exists(file_path):
        return "File not found", 404

    # Obtener tamaño del archivo
    file_size = os.path.getsize(file_path)

    # Obtener rango de bytes si existe
    range_header = request.headers.get("Range")

    if range_header:
        # Parsear rango
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1

        # Limitar el rango
        if end >= file_size:
            end = file_size - 1

        # Calcular tamaño del chunk
        chunk_size = end - start + 1

        # Leer el chunk
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(chunk_size)

        # Headers de respuesta
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": chunk_size,
            "Content-Type": "video/mp4",
        }

        total_time = time.time() - start_total
        logger.info(f"⏱️ Range request TOTAL: {total_time:.3f}s")

        return Response(data, status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")

        # Enviar archivo completo
        return send_file(
            file_path, mimetype="video/mp4", as_attachment=False, download_name=filename
        )


@streaming_bp.route("/info/<path:filename>")
def video_info(filename):
    """Información del video"""
    movies_folder = os.environ.get("MOVIES_FOLDER", "/mnt/DATA_2TB/audiovisual")
    file_path = os.path.join(movies_folder, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    file_size = os.path.getsize(file_path)
    return jsonify(
        {
            "filename": filename,
            "size": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
        }
    )


@streaming_bp.route("/path/<path:file_path>")
def stream_video_by_path(file_path):
    """
    Streaming directo por ruta, SIN pasar por el repositorio.

    Args:
        file_path: Ruta relativa al archivo (ej: data/movies/series/Doom Patrol/S01/...)
                   o ruta absoluta (/mnt/DATA_2TB/audiovisual/...)
    """
    import time
    import logging
    import urllib.parse
    from flask import send_file, request, Response
    from src.infrastructure.config.settings import settings

    logger = logging.getLogger(__name__)
    start_total = time.time()

    BUFFER_SIZE = 1024 * 1024  # 1MB buffer

    file_path = urllib.parse.unquote(file_path)

    if ".." in file_path:
        logger.warning(f"⚠️ Intento de path traversal detectado: {file_path}")
        return "Invalid path", 400

    # Manejar rutas absolutas del contenedor (/mnt/DATA_2TB/audiovisual/...)
    # La ruta puede venir con o sin /
    if file_path.startswith("/mnt/") or file_path.startswith("mnt/"):
        original_path = file_path
        if file_path.startswith("/"):
            full_path = file_path
        else:
            full_path = "/" + file_path
        logger.info(f"Ruta absoluta detectada: '{full_path}'")
        clean_path = ""
    else:
        # Rutas relativas tradicionales
        movies_base = "/data/movies"
        original_path = file_path
        clean_path = file_path

        if clean_path.startswith("data/movies/"):
            clean_path = clean_path[len("data/movies/") :]
            logger.info(f"Ruta limpiada: '{original_path}' → '{clean_path}'")

        if not clean_path.startswith("/"):
            full_path = os.path.join(movies_base, clean_path)
        else:
            full_path = clean_path

    full_path = os.path.normpath(full_path)

    logger.info(f"🎬 Streaming directo por ruta: {original_path}")
    logger.info(f"📁 Ruta limpia: {clean_path}")
    logger.info(f"📁 Ruta completa: {full_path}")

    if not os.path.exists(full_path):
        logger.warning(f"⚠️ Archivo no encontrado: {full_path}")
        return "File not found", 404

    logger.info(f"✅ Archivo encontrado: {full_path}")

    # Obtener tamaño del archivo
    start_size = time.time()
    file_size = os.path.getsize(full_path)
    size_time = time.time() - start_size
    logger.info(f"⏱️ File size: {size_time:.3f}s - {file_size / 1024 / 1024:.2f}MB")

    # Obtener rango de bytes si existe
    range_header = request.headers.get("Range")

    if range_header:
        # Parsear rango
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1

        # Limitar el rango
        if end >= file_size:
            end = file_size - 1

        # Calcular tamaño del chunk
        chunk_size = end - start + 1

        logger.info(
            f"📡 Range: {start}-{end} ({chunk_size / 1024 / 1024:.1f}MB) - Buffer: {BUFFER_SIZE / 1024}KB"
        )

        # Generador con buffer grande para streaming eficiente
        def generate_large_chunks():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(BUFFER_SIZE, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        # Headers de respuesta
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": "video/mp4",
        }

        total_time = time.time() - start_total
        logger.info(f"⏱️ Range request TOTAL: {total_time:.3f}s")

        return Response(generate_large_chunks(), status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")

        # Enviar archivo completo
        ext = os.path.splitext(full_path)[1].lower()
        mimetype = "video/x-matroska" if ext == ".mkv" else "video/mp4"

        return send_file(
            full_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=os.path.basename(full_path),
        )


@streaming_bp.route("/serie/<slug>/<int:season>/<int:episode>")
def stream_serie_by_slug(slug: str, season: int, episode: int):
    """
    Streaming de episodio por slug de serie.
    GET /api/streaming/serie/{slug}/{season}/{episode}

    Args:
        slug: Slug/título de la serie
        season: Número de temporada
        episode: Número de episodio
    """
    import time
    import logging
    import re
    from flask import send_file, request, Response

    logger = logging.getLogger(__name__)
    start_total = time.time()

    BUFFER_SIZE = 1024 * 1024  # 1MB buffer

    series_folder = (
        os.environ.get("MOVIES_FOLDER", "/mnt/DATA_2TB/audiovisual") + "/series"
    )

    logger.info(f"📺 Streaming serie: slug={slug}, S{season:02d}E{episode:02d}")

    title = slug.replace("-", " ").replace("_", " ").strip()
    title = title.title()

    serie_path = None
    for item in os.listdir(series_folder):
        item_path = os.path.join(series_folder, item)
        if os.path.isdir(item_path):
            clean_item = item.replace(".", " ").strip().lower()
            if (
                clean_item == title.lower()
                or title.lower() in clean_item
                or clean_item in title.lower()
            ):
                serie_path = item_path
                break

    if not serie_path:
        logger.warning(f"⚠️ Serie no encontrada: {title}")
        return "Serie not found", 404

    season_folder = f"S{season:02d}"
    season_path = os.path.join(serie_path, season_folder)

    if not os.path.isdir(season_path):
        logger.warning(f"⚠️ Temporada no encontrada: {season_folder}")
        return "Season not found", 404

    pattern = re.compile(rf"[Ss]?\d+[Ee]?{episode:02d}", re.IGNORECASE)
    file_path = None

    for file in os.listdir(season_path):
        if pattern.search(file):
            ext = os.path.splitext(file)[1].lower()
            if ext in {".mkv", ".mp4", ".avi", ".mov", ".flv", ".wmv"}:
                file_path = os.path.join(season_path, file)
                break

    if not file_path:
        logger.warning(f"⚠️ Episodio no encontrado: S{season:02d}E{episode:02d}")
        return "Episode not found", 404

    logger.info(f"✅ Archivo encontrado: {file_path}")

    if not os.path.exists(file_path):
        return "File not found", 404

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    ext = os.path.splitext(file_path)[1].lower()
    mime_type = "video/x-matroska" if ext == ".mkv" else "video/mp4"

    if range_header:
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1

        if end >= file_size:
            end = file_size - 1

        chunk_size = end - start + 1

        def generate_chunks():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(BUFFER_SIZE, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": mime_type,
        }

        return Response(generate_chunks(), status=206, headers=headers)
    else:
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=os.path.basename(file_path),
        )


@streaming_bp.route("/id/<movie_id>")
def stream_video_by_id(movie_id):
    """Streaming de video usando ID de película (desde caché) - Optimizado para NAS"""
    import time
    import logging
    import urllib.parse
    from flask import send_file, request, Response

    logger = logging.getLogger(__name__)
    start_total = time.time()

    logger.info(f"🎬 Streaming por ID: {movie_id}")

    # Buffer grande para mejor rendimiento en NAS/HDD
    BUFFER_SIZE = 1024 * 1024  # 1MB buffer

    # Usar el repositorio para obtener la película por ID (usa caché)
    try:
        from src.adapters.config.dependencies import get_movie_repository

        repo = get_movie_repository()
        movie = repo.get_by_id(movie_id)

        if not movie:
            logger.warning(f"⚠️ Película no encontrada: {movie_id}")
            return "Movie not found", 404

        file_path = movie["path"]
        logger.info(f"✅ ID {movie_id} -> {file_path}")

    except Exception as e:
        logger.error(f"❌ Error obteniendo película {movie_id}: {e}")
        return f"Error: {str(e)}", 500

    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ Archivo no encontrado: {file_path}")
        return "File not found", 404

    # Obtener tamaño del archivo
    start_size = time.time()
    file_size = os.path.getsize(file_path)
    size_time = time.time() - start_size
    logger.info(f"⏱️ File size: {size_time:.3f}s - {file_size / 1024 / 1024:.2f}MB")

    # Obtener rango de bytes si existe
    range_header = request.headers.get("Range")

    if range_header:
        # Parsear rango
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1

        # Limitar el rango
        if end >= file_size:
            end = file_size - 1

        # Calcular tamaño del chunk
        chunk_size = end - start + 1

        logger.info(
            f"📡 Range: {start}-{end} ({chunk_size / 1024 / 1024:.1f}MB) - Buffer: {BUFFER_SIZE / 1024}KB"
        )

        # Generador con buffer grande para streaming eficiente
        def generate_large_chunks():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(BUFFER_SIZE, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        # Headers de respuesta
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": "video/mp4",
        }

        total_time = time.time() - start_total
        logger.info(f"⏱️ Range request TOTAL: {total_time:.3f}s")

        return Response(generate_large_chunks(), status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")

        # Enviar archivo completo
        ext = os.path.splitext(full_path)[1].lower()
        mimetype = "video/x-matroska" if ext == ".mkv" else "video/mp4"

        return send_file(
            full_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=os.path.basename(full_path),
        )


@streaming_bp.route("/episode/<episode_id>")
def stream_episode_by_id(episode_id):
    """Streaming de video usando ID de episodio"""
    import time
    import logging
    import urllib.parse
    from flask import send_file, request, Response

    logger = logging.getLogger(__name__)
    start_total = time.time()

    logger.info(f"📺 Streaming de episodio: {episode_id}")

    # Buffer grande para mejor rendimiento en NAS/HDD
    BUFFER_SIZE = 1024 * 1024  # 1MB buffer

    # Usar el repositorio de series para obtener el episodio
    try:
        from src.adapters.config.dependencies import get_serie_repository
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()
        series_folder = settings.SERIES_FOLDER

        serie_repo = get_serie_repository()

        if not serie_repo:
            logger.error("❌ Repositorio de series no disponible")
            return "Serie repository not available", 500

        # Buscar el episodio
        episode = None
        series = serie_repo.list_all()

        for serie in series:
            episodes = serie.get("episodes", [])
            for ep in episodes:
                ep_id = str(ep.get("id") or ep.get("episode_id") or "")
                if ep_id == episode_id or ep_id == episode_id.replace("ep_", ""):
                    episode = ep
                    break
            if episode:
                break

        if not episode:
            logger.warning(f"⚠️ Episodio no encontrado: {episode_id}")
            return "Episode not found", 404

        # Obtener la ruta del archivo
        filename = episode.get("filename")

        # Buscar en las carpetas de series
        if not series_folder:
            series_folder = "/mnt/servidor/Data2TB/audiovisual/series"

        # Buscar el archivo en la carpeta de la serie
        serie_name = episode.get("serie_name", "")
        season = episode.get("season", 1)

        # Construir posibles rutas
        possible_paths = [
            os.path.join(series_folder, serie_name, f"Season {season}", filename),
            os.path.join(series_folder, serie_name, filename),
            os.path.join(series_folder, filename),
        ]

        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            logger.warning(
                f"⚠️ Archivo de episodio no encontrado en ninguna ruta: {possible_paths}"
            )
            return "File not found", 404

        logger.info(f"✅ Episodio {episode_id} -> {file_path}")

    except Exception as e:
        logger.error(f"❌ Error obteniendo episodio {episode_id}: {e}")
        return f"Error: {str(e)}", 500

    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ Archivo no encontrado: {file_path}")
        return "File not found", 404

    # Obtener tamaño del archivo
    start_size = time.time()
    file_size = os.path.getsize(file_path)
    size_time = time.time() - start_size
    logger.info(f"⏱️ File size: {size_time:.3f}s - {file_size / 1024 / 1024:.2f}MB")

    # Obtener rango de bytes si existe
    range_header = request.headers.get("Range")

    if range_header:
        # Parsear rango
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1

        # Limitar el rango
        if end >= file_size:
            end = file_size - 1

        # Calcular tamaño del chunk
        chunk_size = end - start + 1

        logger.info(f"📡 Range: {start}-{end} ({chunk_size / 1024 / 1024:.1f}MB)")

        # Generador con buffer grande para streaming eficiente
        def generate_large_chunks():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(BUFFER_SIZE, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        # Headers de respuesta
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": "video/mp4",
        }

        total_time = time.time() - start_total
        logger.info(f"⏱️ Range request TOTAL: {total_time:.3f}s")

        return Response(generate_large_chunks(), status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")

        # Enviar archivo completo
        ext = os.path.splitext(full_path)[1].lower()
        mimetype = "video/x-matroska" if ext == ".mkv" else "video/mp4"

        return send_file(
            full_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=os.path.basename(full_path),
        )
