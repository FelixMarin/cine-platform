"""
Adaptador de entrada - Rutas de reproductor
Blueprint para streaming y seguimiento de progreso
"""

import os
import re
import urllib.parse
from flask import (
    Blueprint,
    jsonify,
    request,
    session,
    Response,
    stream_with_context,
    render_template,
)
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.services.translation import translate_plot_async
from src.infrastructure.models.catalog import OmdbEntry, LocalContent

# Importar casos de uso (se inicializan después)
from src.core.use_cases.player import (
    StreamMovieUseCase,
    StreamEpisodeUseCase,
    TrackProgressUseCase,
    GetContinueWatchingUseCase,
    GetWatchedContentUseCase,
)

from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


player_bp = Blueprint("player", __name__)

# Blueprint para la página de reproducción (sin prefijo /api)
player_page_bp = Blueprint("player_page", __name__)


def clean_filename(filename):
    """Limpia el nombre del archivo para mostrar"""
    name = re.sub(r"[-_]?optimized", "", filename, flags=re.IGNORECASE)
    name = re.sub(r"\.(mkv|mp4|avi|mov)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[._-]", " ", name)
    return " ".join(word.capitalize() for word in name.split())


@player_page_bp.route("/play/<path:media_path>")
@require_auth
def play_page(media_path):
    """Página de reproducción de video"""
    # URL decode the path
    filename = urllib.parse.unquote(media_path)

    # Limpiar el nombre para mostrar
    basename = os.path.basename(filename)
    sanitized_name = clean_filename(basename)

    # Verificar si el usuario es admin
    is_admin = session.get("user_role") == "admin"

    # Extraer año
    year = None
    year_match = re.search(r"\((\d{4})\)", basename)
    if year_match:
        year = int(year_match.group(1))

    # Extraer título limpio
    clean_title = re.sub(r"\(.*?\)", "", basename)
    clean_title = re.sub(r"[-_]?optimized", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\.(mkv|mp4|avi|mov)$", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"[._-]", " ", clean_title).strip()

    return render_template(
        "pages/movies/play.html",
        filename=filename,
        sanitized_name=sanitized_name,
        media_path=media_path,
        clean_title=clean_title,
        year=year,
        is_admin=is_admin,
        use_direct_path=True,
    )


@player_page_bp.route("/play/id/<movie_id>")
def play_page_by_id(movie_id):
    """Página de reproducción usando ID de película"""
    from src.adapters.config.dependencies import get_movie_repository
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"🎬 play_page_by_id: {movie_id}")

    # Verificar si el usuario es admin
    is_admin = session.get("user_role") == "admin"

    try:
        repo = get_movie_repository()
        movie = repo.get_by_id(movie_id)

        if not movie:
            logger.warning(f"⚠️ Película no encontrada: {movie_id}")
            return "Película no encontrada", 404

        filename = movie["path"]
        basename = os.path.basename(filename)
        sanitized_name = clean_filename(basename)

        year = movie.get("year")
        clean_title = movie.get("title", sanitized_name)

        logger.info(f"✅ Reproduciendo: {clean_title} ({year})")

        return render_template(
            "pages/movies/play.html",
            filename=filename,
            sanitized_name=sanitized_name,
            media_path=movie_id,
            clean_title=clean_title,
            year=year,
            movie_id=movie_id,
            is_admin=is_admin,
            use_direct_path=True,
        )

    except Exception as e:
        logger.error(f"❌ Error en play_page_by_id: {e}")
        return f"Error: {str(e)}", 500


@player_page_bp.route("/play")
def play_page_root():
    """Página de reproducción (raíz)"""
    return render_template(
        "pages/movies/play.html", filename="", sanitized_name="Reproducción", media_path=""
    )


@player_page_bp.route("/play/serie/<int:serie_id>/<int:season>/<int:episode>")
def play_serie_episode(serie_id, season, episode):
    """
    Reproduce un episodio específico de una serie.
    Construye la ruta del archivo basándose en la estructura normalizada.
    """
    import logging
    from flask import redirect

    logger = logging.getLogger(__name__)
    logger.info(
        f"Reproduciendo serie: {serie_id}, temporada {season}, episodio {episode}"
    )

    is_admin = session.get("user_role") == "admin"

    try:
        from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
            get_catalog_repository,
            get_catalog_repository_session,
        )

        with get_catalog_repository_session() as db:
            # 1. Buscar la serie en omdb_entries por ID
            serie = db.query(OmdbEntry).filter(
                OmdbEntry.id == serie_id,
                OmdbEntry.type == "series"
            ).first()
            
            if not serie:
                # Fallback: buscar en local_content
                repo = get_catalog_repository(db)
                serie = repo.get_local_content_by_id(serie_id)
                if not serie or serie.type != "series":
                    logger.warning(f"Serie no encontrada: {serie_id}")
                    return "Serie no encontrada", 404
            
            # 2. Buscar la ruta física en local_content por título o imdb_id
            local_content = db.query(LocalContent).filter(
                LocalContent.title == serie.title,
                LocalContent.type == "series"
            ).first()
            
            if not local_content and serie.imdb_id:
                local_content = db.query(LocalContent).filter(
                    LocalContent.imdb_id == serie.imdb_id,
                    LocalContent.type == "series"
                ).first()
            
            serie_folder = local_content.file_path if local_content else None
            
            if not serie_folder or not os.path.exists(serie_folder):
                logger.error(f"Ruta de serie no válida: {serie_folder}")
                return "Ruta de serie no válida", 404

            season_folder = f"S{season:02d}"
            season_path = os.path.join(serie_folder, season_folder)

            if not os.path.exists(season_path):
                logger.error(f"Temporada no encontrada: {season_path}")
                return "Temporada no encontrada", 404

            possible_names = [
                serie.title.replace(" ", "-"),
                serie.title.replace(" ", ""),
                os.path.basename(serie_folder).replace(" ", "-"),
            ]

            if "12 Monkeys" in serie.title:
                possible_names.append("12-Monos")

            file_path = None
            for base_name in possible_names:
                if base_name:
                    episode_filename = (
                        f"{base_name}-S{season:02d}E{episode:02d}-serie.mkv"
                    )
                    test_path = os.path.join(season_path, episode_filename)
                    if os.path.exists(test_path):
                        file_path = test_path
                        logger.info(
                            f"Archivo encontrado con patrón '{base_name}': {episode_filename}"
                        )
                        break

            if not file_path:
                pattern = re.compile(rf"S{season:02d}E{episode:02d}", re.IGNORECASE)
                for f in os.listdir(season_path):
                    if pattern.search(f) and f.endswith(".mkv"):
                        file_path = os.path.join(season_path, f)
                        logger.info(
                            f"Archivo encontrado por patrón S{season:02d}E{episode:02d}: {f}"
                        )
                        break

            if not file_path:
                logger.error(
                    f"No se encontró archivo para temporada {season}, episodio {episode}"
                )
                return "Episodio no encontrado", 404

            logger.info(f"✅ Episodio encontrado: {file_path}")

            from src.infrastructure.config.settings import settings

            movies_base = settings.MOVIES_BASE_PATH
            if file_path.startswith(movies_base):
                rel_path = os.path.relpath(file_path, movies_base)
            else:
                rel_path = file_path

            rel_path = rel_path.lstrip("/")

            filename = os.path.basename(file_path)
            sanitized_name = f"{serie.title} - T{season:02d}E{episode:02d}"

            year = getattr(serie, "year", None)

            return render_template(
                "pages/movies/play.html",
                filename=rel_path,
                sanitized_name=sanitized_name,
                media_path=f"{serie_id}/{season}/{episode}",
                clean_title=serie.title,
                year=year,
                is_admin=is_admin,
                serie_id=serie_id,
                season=season,
                episode=episode,
                use_direct_path=True,
            )

    except Exception as e:
        logger.error(f"Error reproduciendo episodio: {e}")
        return f"Error: {str(e)}", 500


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
    get_watched_content_use_case: GetWatchedContentUseCase = None,
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
    return session.get("user_id", 0)


# === ENDPOINTS DE METADATOS (ASÍNCRONO) ===


@player_bp.route("/api/movie/metadata", methods=["GET"])
def get_movie_metadata():
    """Endpoint para obtener metadatos de una película de forma asíncrona"""
    title = request.args.get("title", "")
    year = request.args.get("year", type=int)

    if not title:
        return jsonify({"error": "title es requerido"}), 400

    movie_info = None
    try:
        from src.adapters.outgoing.services.omdb.cached_client import (
            OMDBMetadataServiceCached,
        )

        omdb_service = OMDBMetadataServiceCached()

        if omdb_service.is_available():
            omdb_data = omdb_service.get_movie_metadata(title, year)

            if omdb_data:
                # Traducir el plot al español (ASÍNCRONO - respuesta inmediata)
                # Si hay traducción cacheada, la retorna inmediatamente
                # Si no, retorna el plot original y traduce en background
                original_plot = omdb_data.get("Plot")
                translated_plot, was_translated, _ = translate_plot_async(
                    original_plot, omdb_data.get("Title")
                )

                movie_info = {
                    "title": omdb_data.get("Title"),
                    "year": omdb_data.get("Year"),
                    "released": omdb_data.get("Released"),
                    "runtime": omdb_data.get("Runtime"),
                    "genre": omdb_data.get("Genre"),
                    "genres": [
                        g.strip()
                        for g in omdb_data.get("Genre", "").split(",")
                        if g.strip()
                    ],
                    "director": omdb_data.get("Director"),
                    "writer": omdb_data.get("Writer"),
                    "actors": omdb_data.get("Actors"),
                    "plot": translated_plot,
                    "plot_translated": was_translated,
                    "language": omdb_data.get("Language"),
                    "country": omdb_data.get("Country"),
                    "awards": omdb_data.get("Awards"),
                    "imdb_rating": omdb_data.get("imdbRating"),
                    "imdb_votes": omdb_data.get("imdbVotes"),
                    "box_office": omdb_data.get("BoxOffice"),
                }

                # Procesar póster
                poster = omdb_data.get("Poster")
                if poster and poster != "N/A":
                    import requests

                    movie_info["poster"] = [
                        f"/proxy-image?url={requests.utils.quote(poster)}",
                        "/static/images/default-poster.jpg",
                    ]
                else:
                    movie_info["poster"] = None

                # Procesar ratings
                ratings = []
                for rating in omdb_data.get("Ratings", []):
                    source = rating.get("Source", "")
                    value = rating.get("Value", "")
                    if "Rotten Tomatoes" in source:
                        ratings.append(f"🍅 {value}")
                    elif "Metacritic" in source:
                        ratings.append(f"📊 {value}")
                    elif "Internet Movie Database" in source:
                        ratings.append(f"⭐ {value}")
                movie_info["ratings"] = ratings

                # Procesar reparto
                movie_info["cast"] = [
                    a.strip()
                    for a in omdb_data.get("Actors", "").split(",")[:5]
                    if a.strip()
                ]

        if movie_info:
            return jsonify(movie_info)
        else:
            return jsonify({"error": "No se encontraron metadatos"}), 404

    except Exception as e:
        logger.error(f"Error en get_movie_metadata: {e}")
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/serie/metadata", methods=["GET"])
def get_serie_metadata():
    """Endpoint para obtener metadatos de una serie de forma asíncrona"""
    title = request.args.get("title", "")

    if not title:
        return jsonify({"error": "title es requerido"}), 400

    try:
        from src.adapters.outgoing.services.omdb.cached_client import (
            OMDBMetadataServiceCached,
        )

        omdb_service = OMDBMetadataServiceCached()

        if omdb_service.is_available():
            # Intentar primero con el título tal cual
            omdb_data = omdb_service.get_serie_metadata(title)

            if not omdb_data:
                logger.warning(
                    f"⚠️ No se encontraron metadatos para '{title}'. Si el título está en español, se requiere traducción manual."
                )

            if omdb_data:
                # Traducir el plot al español (ASÍNCRONO - respuesta inmediata)
                # Si hay traducción cacheada, la retorna inmediatamente
                # Si no, retorna el plot original y traduce en background
                original_plot = omdb_data.get("Plot")
                translated_plot, was_translated, _ = translate_plot_async(
                    original_plot, omdb_data.get("Title")
                )

                serie_info = {
                    "title": omdb_data.get("Title"),
                    "year": omdb_data.get("Year"),
                    "released": omdb_data.get("Released"),
                    "runtime": omdb_data.get("Runtime"),
                    "genre": omdb_data.get("Genre"),
                    "genres": [
                        g.strip()
                        for g in omdb_data.get("Genre", "").split(",")
                        if g.strip()
                    ],
                    "director": omdb_data.get("Director"),
                    "writer": omdb_data.get("Writer"),
                    "actors": omdb_data.get("Actors"),
                    "plot": translated_plot,
                    "plot_translated": was_translated,
                    "language": omdb_data.get("Language"),
                    "country": omdb_data.get("Country"),
                    "awards": omdb_data.get("Awards"),
                    "imdb_rating": omdb_data.get("imdbRating"),
                    "imdb_votes": omdb_data.get("imdbVotes"),
                    "total_seasons": omdb_data.get("totalSeasons"),
                }

                # Procesar póster
                poster = omdb_data.get("Poster")
                if poster and poster != "N/A":
                    import requests

                    serie_info["poster"] = [
                        f"/proxy-image?url={requests.utils.quote(poster)}",
                        "/static/images/default-poster.jpg",
                    ]
                else:
                    serie_info["poster"] = None

                # Procesar ratings
                ratings = []
                for rating in omdb_data.get("Ratings", []):
                    source = rating.get("Source", "")
                    value = rating.get("Value", "")
                    if "Rotten Tomatoes" in source:
                        ratings.append(f"🍅 {value}")
                    elif "Metacritic" in source:
                        ratings.append(f"📊 {value}")
                    elif "Internet Movie Database" in source:
                        ratings.append(f"⭐ {value}")
                serie_info["ratings"] = ratings

                # Procesar reparto
                serie_info["cast"] = [
                    a.strip()
                    for a in omdb_data.get("Actors", "").split(",")[:5]
                    if a.strip()
                ]

                return jsonify(serie_info)

        return jsonify({"error": "No se encontraron metadatos"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === ENDPOINTS DE STREAMING ===


@player_bp.route("/api/stream/movie/<int:movie_id>", methods=["GET"])
def stream_movie(movie_id):
    """Endpoint para obtener información de streaming de película"""
    global _stream_movie_use_case

    if _stream_movie_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        stream_info = _stream_movie_use_case.execute(movie_id)

        if not stream_info:
            return jsonify({"error": "Película no encontrada"}), 404

        return jsonify(stream_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/stream/episode/<int:episode_id>", methods=["GET"])
def stream_episode(episode_id):
    """Endpoint para obtener información de streaming de episodio"""
    global _stream_episode_use_case

    if _stream_episode_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        stream_info = _stream_episode_use_case.execute(episode_id)

        if not stream_info:
            return jsonify({"error": "Episodio no encontrado"}), 404

        return jsonify(stream_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === ENDPOINTS DE PROGRESO ===


@player_bp.route("/api/progress", methods=["POST"])
def update_progress():
    """Actualiza el progreso de reproducción"""
    global _track_progress_use_case

    if _track_progress_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        data = request.get_json()

        user_id = get_user_id()
        media_type = data.get("media_type", "movie")
        media_id = data.get("media_id")
        position = data.get("position", 0)
        duration = data.get("duration", 0)

        if not media_id:
            return jsonify({"error": "media_id es requerido"}), 400

        progress = _track_progress_use_case.update_position(
            user_id=user_id,
            media_type=media_type,
            media_id=media_id,
            position=position,
            duration=duration,
        )

        return jsonify(progress)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/progress/complete", methods=["POST"])
def mark_completed():
    """Marca un contenido como completado"""
    global _track_progress_use_case

    if _track_progress_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        data = request.get_json()

        user_id = get_user_id()
        media_type = data.get("media_type", "movie")
        media_id = data.get("media_id")

        if not media_id:
            return jsonify({"error": "media_id es requerido"}), 400

        progress = _track_progress_use_case.mark_completed(
            user_id=user_id, media_type=media_type, media_id=media_id
        )

        return jsonify(progress)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/progress/<media_type>/<int:media_id>", methods=["GET"])
def get_progress(media_type, media_id):
    """Obtiene el progreso de un contenido específico"""
    global _track_progress_use_case

    if _track_progress_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        user_id = get_user_id()

        progress = _track_progress_use_case.get_progress(
            user_id=user_id, media_type=media_type, media_id=media_id
        )

        if not progress:
            return jsonify({"position": 0, "duration": 0, "is_completed": False})

        return jsonify(progress)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === ENDPOINTS DE "SEGUIR VIENDO" ===


@player_bp.route("/api/continue-watching", methods=["GET"])
def get_continue_watching():
    """Obtiene los contenidos que el usuario está viendo"""
    global _get_continue_watching_use_case

    if _get_continue_watching_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        user_id = get_user_id()
        limit = request.args.get("limit", 10, type=int)

        content = _get_continue_watching_use_case.execute(user_id=user_id, limit=limit)

        return jsonify(content)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/watched", methods=["GET"])
def get_watched():
    """Obtiene los contenidos vistos por el usuario"""
    global _get_watched_content_use_case

    if _get_watched_content_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        user_id = get_user_id()
        limit = request.args.get("limit", 20, type=int)

        content = _get_watched_content_use_case.execute(user_id=user_id, limit=limit)

        return jsonify(content)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
