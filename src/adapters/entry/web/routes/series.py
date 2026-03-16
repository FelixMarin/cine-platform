"""
Rutas para series - Endpoints para obtener temporadas y episodios
"""

import os
import re
from flask import Blueprint, jsonify, request, render_template
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)
from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

series_bp = Blueprint("series", __name__, url_prefix="/api")
series_page_bp = Blueprint("series_page", __name__, url_prefix="", template_folder="../../templates")


# Rutas de página (sin prefijo /api)
# Nota: El orden de estas rutas es importante. Flask usa la primera coincidencia.
# También agregamos una ruta catch-all como fallback.

@series_page_bp.route("/series", methods=["GET"])
def series_page():
    """
    Página principal con la pestaña de series activa.
    """
    return render_template("index.html")


@series_page_bp.route("/series/<int:serie_id>", methods=["GET"])
def serie_detail_page(serie_id):
    """
    Página de detalle de una serie específica.
    """
    return render_template("index.html")


@series_page_bp.route("/series/<int:serie_id>/seasons", methods=["GET"])
def serie_seasons_page(serie_id):
    """
    Página de temporadas de una serie específica.
    """
    return render_template("index.html")


@series_page_bp.route("/series/<int:serie_id>/season/<int:season_num>", methods=["GET"])
def serie_season_page(serie_id, season_num):
    """
    Página de episodios de una temporada específica.
    """
    return render_template("index.html")


# Ruta catch-all para cualquier ruta /series que no coincida con las anteriores
@series_page_bp.route("/series/<path:path>", methods=["GET"])
def series_catch_all(path):
    """
    Ruta catch-all para series - maneja cualquier ruta no coincidente.
    """
    return render_template("index.html")


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
            series = repo.list_series(limit=limit, offset=offset)
            return jsonify(
                {
                    "series": [s.to_dict() for s in series],
                    "count": len(series),
                    "limit": limit,
                    "offset": offset,
                }
            )
    except Exception as e:
        logger.error(f"Error listando series: {e}")
        return jsonify({"error": str(e)}), 500


@series_bp.route("/series/<int:serie_id>/seasons", methods=["GET"])
def get_serie_seasons(serie_id):
    """
    Devuelve las temporadas disponibles de una serie.
    Escanea las carpetas S01, S02, etc. en la ruta de la serie.
    """
    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            serie = repo.get_local_content_by_id(serie_id)

            if not serie or serie.type != "series":
                return jsonify({"error": "Serie no encontrada"}), 404

            serie_path = serie.file_path
            if not serie_path or not os.path.exists(serie_path):
                return jsonify({"error": "Ruta de serie no valida"}), 404

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

            seasons.sort(key=lambda x: x["season"])
            return jsonify(
                {"serie_id": serie_id, "serie_title": serie.title, "seasons": seasons}
            )
    except Exception as e:
        logger.error(f"Error obteniendo temporadas: {e}")
        return jsonify({"error": str(e)}), 500


@series_bp.route("/series/<int:serie_id>/season/<int:season>/episodes", methods=["GET"])
def get_season_episodes(serie_id, season):
    """
    Devuelve los episodios de una temporada especifica.
    Escanea los archivos en la carpeta S01, S02, etc.
    Formato esperado: Nombre-Serie-S01E01-serie.mkv
    """
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            serie = repo.get_local_content_by_id(serie_id)

            if not serie or serie.type != "series":
                return jsonify({"error": "Serie no encontrada"}), 404

            serie_path = serie.file_path
            if not serie_path or not os.path.exists(serie_path):
                return jsonify({"error": "Ruta de serie no valida"}), 404

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
                    "serie_title": serie.title,
                    "season": season,
                    "episodes": episodes,
                }
            )
    except Exception as e:
        logger.error(f"Error obteniendo episodios: {e}")
        return jsonify({"error": str(e)}), 500
