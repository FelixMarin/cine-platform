"""
Rutas para series - Endpoints para obtener temporadas y episodios
"""

import os
import re

from flask import Blueprint, jsonify, render_template, request

from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)
from src.infrastructure.config.settings import settings
from src.infrastructure.logging import setup_logging
from src.adapters.outgoing.repositories.postgresql.models.catalog import LocalContent, OmdbEntry

logger = setup_logging(os.environ.get("LOG_FOLDER"))

series_bp = Blueprint("series", __name__, url_prefix="/api")
# Ruta absoluta para el template_folder del Blueprint
_series_template_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
)
series_page_bp = Blueprint(
    "series_page", __name__, url_prefix="", template_folder=_series_template_path
)


# Rutas de página (sin prefijo /api)
# Nota: El orden de estas rutas es importante. Flask usa la primera coincidencia.
# También agregamos una ruta catch-all como fallback.


@series_page_bp.route("/series", methods=["GET"])
def series_page():
    """
    Página principal con la pestaña de series activa.
    """
    return render_template("pages/movies/index.html")


@series_page_bp.route("/series/<int:serie_id>", methods=["GET"])
def serie_detail_page(serie_id):
    """
    Página de detalle de una serie específica.
    """
    return render_template("pages/movies/index.html")


@series_page_bp.route("/series/<int:serie_id>/seasons", methods=["GET"])
def serie_seasons_page(serie_id):
    """
    Página de temporadas de una serie específica.
    """
    return render_template("pages/movies/index.html")


@series_page_bp.route("/series/<int:serie_id>/season/<int:season_num>", methods=["GET"])
def serie_season_page(serie_id, season_num):
    """
    Página de episodios de una temporada específica.
    """
    return render_template("pages/movies/index.html")


# Ruta catch-all para cualquier ruta /series que no coincida con las anteriores
@series_page_bp.route("/series/<path:path>", methods=["GET"])
def series_catch_all(path):
    """
    Ruta catch-all para series - maneja cualquier ruta no coincidente.
    """
    return render_template("pages/movies/index.html")


@series_bp.route("/series", methods=["GET"])
def get_all_series():
    """
    Devuelve todas las series del catalogo local.
    """
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            series = repo.list_all_series_combined(limit=limit, offset=offset)
            return jsonify(
                {
                    "series": series,
                    "count": len(series),
                    "limit": limit,
                    "offset": offset,
                }
            )
    except Exception as e:
        logger.error(f"Error listando series: {e}")
        return jsonify({"error": str(e)}), 500


@series_bp.route("/<int:serie_id>/seasons", methods=["GET"])
def get_serie_seasons(serie_id):
    """
    Devuelve las temporadas disponibles de una serie.
    Busca la serie en omdb_entries y su ruta física en local_content.
    """
    logger.info(f"[get_serie_seasons] INICIO - serie_id={serie_id}")
    try:
        with get_catalog_repository_session() as db:
            # 1. Buscar la serie en omdb_entries por ID
            logger.info("[get_serie_seasons] Buscando en omdb_entries...")
            serie = (
                db.query(OmdbEntry)
                .filter(OmdbEntry.id == serie_id, OmdbEntry.type == "series")
                .first()
            )
            logger.info(f"[get_serie_seasons] omdb_entries result: {serie}")

            if not serie:
                logger.info(
                    "[get_serie_seasons] No encontrado en omdb_entries, buscando en local_content..."
                )
                # Fallback: buscar en local_content si no está en omdb_entries
                repo = get_catalog_repository(db)
                serie = repo.get_local_content_by_id(serie_id)
                logger.info(
                    f"[get_serie_seasons] local_content fallback result: {serie}"
                )
                if not serie or serie.type != "series":
                    logger.error(
                        "[get_serie_seasons] Serie no encontrada en local_content"
                    )
                    return jsonify({"error": "Serie no encontrada"}), 404

            serie_title = serie.title
            logger.info(f"[get_serie_seasons] serie_title: {serie_title}")

            # 2. Buscar la ruta física en local_content por título o imdb_id
            logger.info(
                "[get_serie_seasons] Buscando file_path en local_content por titulo..."
            )
            local_content = (
                db.query(LocalContent)
                .filter(
                    LocalContent.title == serie_title, LocalContent.type == "series"
                )
                .first()
            )
            logger.info(
                f"[get_serie_seasons] local_content por titulo: {local_content}"
            )

            if not local_content and serie.imdb_id:
                logger.info(
                    f"[get_serie_seasons] Buscando file_path en local_content por imdb_id={serie.imdb_id}"
                )
                local_content = (
                    db.query(LocalContent)
                    .filter(
                        LocalContent.imdb_id == serie.imdb_id,
                        LocalContent.type == "series",
                    )
                    .first()
                )
                logger.info(
                    f"[get_serie_seasons] local_content por imdb_id: {local_content}"
                )

            if local_content and local_content.file_path:
                serie_path = local_content.file_path
                logger.info(
                    f"[get_serie_seasons] Usando local_content.file_path: {serie_path}"
                )
            else:
                logger.info(
                    "[get_serie_seasons] No hay local_content.file_path, usando fallback..."
                )
                series_base = getattr(
                    settings, "SERIES_FOLDER", "/mnt/DATA_2TB/audiovisual/series"
                )
                serie_path = os.path.join(series_base, serie_title)
                logger.info(f"[get_serie_seasons] Fallback path: {serie_path}")

            logger.info(f"[get_serie_seasons]serie_path final: {serie_path}")
            logger.info(
                f"[get_serie_seasons] os.path.exists check: {os.path.exists(serie_path)}"
            )

            if not os.path.exists(serie_path):
                logger.error(
                    f"[get_serie_seasons] Ruta no existe en disco: {serie_path}"
                )
                return jsonify({"error": "Ruta de serie no valida en disco"}), 404

            logger.info("[get_serie_seasons] Escaneando carpetas de temporada...")
            season_pattern = re.compile(r"^S(\d+)$", re.IGNORECASE)
            seasons = []

            try:
                for item in os.listdir(serie_path):
                    item_path = os.path.join(serie_path, item)
                    if os.path.isdir(item_path):
                        match = season_pattern.match(item)
                        if match:
                            seasons.append(
                                {"season": int(match.group(1)), "folder": item}
                            )
            except Exception as e:
                logger.error(f"Error leyendo carpetas de temporada: {e}")
                return jsonify({"error": str(e)}), 500

            logger.info(f"[get_serie_seasons] Temporadas encontradas: {seasons}")
            seasons.sort(key=lambda x: x["season"])
            return jsonify(
                {"serie_id": serie_id, "serie_title": serie_title, "seasons": seasons}
            )
    except Exception as e:
        logger.error(f"Error obteniendo temporadas: {e}")
        return jsonify({"error": str(e)}), 500


@series_bp.route("/<int:serie_id>/season/<int:season>/episodes", methods=["GET"])
def get_season_episodes(serie_id, season):
    """
    Devuelve los episodios de una temporada especifica.
    Busca la serie en omdb_entries y su ruta física en local_content.
    """
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

    try:
        with get_catalog_repository_session() as db:
            # 1. Buscar la serie en omdb_entries por ID
            serie = (
                db.query(OmdbEntry)
                .filter(OmdbEntry.id == serie_id, OmdbEntry.type == "series")
                .first()
            )

            if not serie:
                # Fallback: buscar en local_content
                repo = get_catalog_repository(db)
                serie = repo.get_local_content_by_id(serie_id)
                if not serie or serie.type != "series":
                    return jsonify({"error": "Serie no encontrada"}), 404

            serie_title = serie.title

            # 2. Buscar la ruta física en local_content por título o imdb_id
            local_content = (
                db.query(LocalContent)
                .filter(
                    LocalContent.title == serie_title, LocalContent.type == "series"
                )
                .first()
            )

            if not local_content and serie.imdb_id:
                local_content = (
                    db.query(LocalContent)
                    .filter(
                        LocalContent.imdb_id == serie.imdb_id,
                        LocalContent.type == "series",
                    )
                    .first()
                )

            if local_content and local_content.file_path:
                serie_path = local_content.file_path
            else:
                series_base = getattr(
                    settings, "SERIES_FOLDER", "/mnt/DATA_2TB/audiovisual/series"
                )
                serie_path = os.path.join(series_base, serie_title)

            if not os.path.exists(serie_path):
                return jsonify({"error": "Ruta de serie no valida en disco"}), 404

            season_folder = "S{:02d}".format(season)
            season_path = os.path.join(serie_path, season_folder)

            if not os.path.exists(season_path):
                return jsonify({"serie_id": serie_id, "season": season, "episodes": []})

            pattern = re.compile(rf"S{season:02d}E(\d+)", re.IGNORECASE)

            episodes = []
            try:
                for f in os.listdir(season_path):
                    file_path = os.path.join(season_path, f)
                    if not os.path.isfile(file_path):
                        continue

                    ext = os.path.splitext(f)[1].lower()
                    if ext not in valid_extensions:
                        continue

                    match = pattern.search(f)
                    if match:
                        episodes.append(
                            {
                                "episode": int(match.group(1)),
                                "filename": f,
                                "file_path": file_path,
                            }
                        )
            except Exception as e:
                logger.error(f"Error leyendo episodios: {e}")
                return jsonify({"error": str(e)}), 500

            episodes.sort(key=lambda x: x["episode"])
            return jsonify(
                {
                    "serie_id": serie_id,
                    "serie_title": serie_title,
                    "season": season,
                    "episodes": episodes,
                }
            )
    except Exception as e:
        logger.error(f"Error obteniendo episodios: {e}")
        return jsonify({"error": str(e)}), 500
