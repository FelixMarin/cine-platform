"""
Adaptador de entrada - Rutas de catálogo de películas
Blueprint para /api/movies con metadata de OMDB
"""

import os
import re
import base64
import logging
from flask import Blueprint, jsonify, request

from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    CatalogRepository,
)
from src.adapters.outgoing.services.omdb.client import OMDBMetadataService
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

catalog_movies_bp = Blueprint("catalog_movies", __name__, url_prefix="/api")

MOVIES_BASE_PATH = "/mnt/DATA_2TB/audiovisual/mkv"
VALID_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".flv", ".wmv"}

CATEGORIES = ["action", "comedia", "drama", "horror", "sci_fi", "terror"]


def _parse_filename(filename: str) -> tuple:
    """
    Parsea el nombre del archivo para extraer título y año.
    Formato: nombre-(año)-optimized.mkv
    """
    name_without_ext = filename.rsplit(".", 1)[0]

    name_clean = name_without_ext
    for suffix in ["-optimized", "-HD", "-4K", "-BluRay", "-WEB", "-DL", "-AC3"]:
        name_clean = name_clean.replace(suffix, "")

    year = None

    year_match = re.search(r"\((\d{4})\)", name_clean)
    if year_match:
        year = int(year_match.group(1))
        name_clean = re.sub(r"\(\d{4}\)", "", name_clean)

    if year is None:
        year_match = re.search(r"[.\-_ ](\d{4})[.\-_ ]", name_clean)
        if year_match:
            year = int(year_match.group(1))
            name_clean = name_clean.replace(year_match.group(0), " ")

    if year is None:
        year_match = re.search(r"(\d{4})$", name_clean.strip())
        if year_match:
            year = int(year_match.group(1))
            name_clean = name_clean[:-4].strip()

    title = name_clean.replace("-", " ").replace("_", " ").strip()
    title = re.sub(r"\s+", " ", title)

    return title, year


def _scan_movies_from_filesystem() -> list:
    """
    Escanea el sistema de archivos para obtener películas.
    Ruta: /mnt/DATA_2TB/audiovisual/mkv/{categoria}/
    """
    movies = []

    if not os.path.exists(MOVIES_BASE_PATH):
        logger.warning(f"La carpeta base no existe: {MOVIES_BASE_PATH}")
        return movies

    for category in CATEGORIES:
        category_path = os.path.join(MOVIES_BASE_PATH, category)
        if not os.path.isdir(category_path):
            continue

        try:
            for entry in os.scandir(category_path):
                if entry.is_file(follow_symlinks=False):
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in VALID_EXTENSIONS:
                        title, year = _parse_filename(entry.name)
                        movies.append(
                            {
                                "title": title,
                                "year": year,
                                "category": category,
                                "file_path": entry.path,
                                "filename": entry.name,
                            }
                        )
        except PermissionError:
            logger.warning(f"Permission denied: {category_path}")

    return movies


def _get_omdb_entry(db: CatalogRepository, title: str, year: int):
    """Busca en omdb_entries por título EXACTO + año EXACTO"""
    return db.get_exact_match(title, year)


def _get_local_content(db: CatalogRepository, title: str, year: int):
    """Busca en local_content por título EXACTO + año EXACTO"""
    from src.infrastructure.models.catalog import LocalContent

    db_session = db._get_db()
    return (
        db_session.query(LocalContent)
        .filter(
            LocalContent.title == title,
            LocalContent.year == str(year),
            LocalContent.type == "movie",
        )
        .first()
    )


def _fetch_and_save_from_omdb(title: str, year: int) -> dict:
    """
    Consulta OMDB API y guarda el resultado.
    Retorna los datos si hay UNA coincidencia exacta, None en caso contrario.
    """
    omdb_service = OMDBMetadataService(settings.OMDB_API_KEY)

    search_results = omdb_service.search_movies(title, year)

    if not search_results:
        return None

    exact_matches = []
    for result in search_results:
        result_title = result.get("Title", "").strip()
        result_year = result.get("Year", "")

        if result_title.lower() == title.lower():
            if year:
                if str(year) in result_year or result_year.startswith(str(year)):
                    exact_matches.append(result)
            else:
                exact_matches.append(result)

    if len(exact_matches) >= 1:
        exact_match = exact_matches[0]

        full_data = omdb_service.get_movie_metadata(exact_match["Title"], year)

        if full_data and full_data.get("Response") != "False":
            poster_bytes = None
            poster_url = full_data.get("Poster")
            if poster_url and poster_url != "N/A":
                try:
                    import requests

                    poster_resp = requests.get(poster_url, timeout=10)
                    if poster_resp.status_code == 200:
                        poster_bytes = poster_resp.content
                except Exception:
                    pass

            with get_catalog_repository() as db:
                db.create_or_update_omdb_entry(full_data, poster_bytes)

            return {"omdb_data": full_data, "poster_bytes": poster_bytes}

    return None


def _save_to_local_content(title: str, year: int, category: str):
    """Guarda en local_content cuando no hay coincidencia exacta en OMDB"""
    with get_catalog_repository() as db:
        db.create_local_content(
            {
                "title": title,
                "year": str(year) if year else None,
                "type": "movie",
                "genre": category.capitalize(),
            }
        )


def _get_poster_base64(poster_bytes: bytes) -> str:
    """Convierte bytes de imagen a base64 data URI"""
    if not poster_bytes:
        return None
    try:
        import base64

        b64 = base64.b64encode(poster_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None


@catalog_movies_bp.route("/movies", methods=["GET"])
@require_auth
def get_movies():
    """
    Obtiene la lista de películas con metadata.

    Flujo:
    1. Escanear sistema de archivos
    2. Buscar en omdb_entries (título + año exacto)
    3. Si no existe, buscar en local_content (título + año exacto)
    4. Si no existe en ninguna tabla, consultar OMDB API
    5. Si hay UNA coincidencia exacta → guardar en omdb_entries
    6. Si NO hay coincidencia exacta → guardar en local_content
    """
    try:
        movies_fs = _scan_movies_from_filesystem()
        logger.info(f"Escaneadas {len(movies_fs)} películas del FS")

        result_movies = []

        with get_catalog_repository() as db:
            for movie in movies_fs:
                title = movie["title"]
                year = movie["year"]
                category = movie["category"]

                omdb_entry = _get_omdb_entry(db, title, year)

                if omdb_entry:
                    result_movies.append(
                        {
                            "title": omdb_entry.title,
                            "year": int(omdb_entry.year)
                            if omdb_entry.year and omdb_entry.year.isdigit()
                            else omdb_entry.year,
                            "category": category,
                            "poster_base64": _get_poster_base64(
                                omdb_entry.poster_image
                            ),
                            "plot": omdb_entry.plot,
                            "genre": omdb_entry.genre,
                            "imdb_rating": float(omdb_entry.imdb_rating)
                            if omdb_entry.imdb_rating
                            else None,
                            "metadata_source": "omdb",
                        }
                    )
                    continue

                local_content = _get_local_content(db, title, year)

                if local_content:
                    result_movies.append(
                        {
                            "title": local_content.title,
                            "year": int(local_content.year)
                            if local_content.year and local_content.year.isdigit()
                            else local_content.year,
                            "category": category,
                            "poster_base64": _get_poster_base64(
                                local_content.poster_image
                            ),
                            "plot": local_content.plot,
                            "genre": local_content.genre,
                            "imdb_rating": float(local_content.imdb_rating)
                            if local_content.imdb_rating
                            else None,
                            "metadata_source": "local",
                        }
                    )
                    continue

                omdb_result = _fetch_and_save_from_omdb(title, year)

                if omdb_result:
                    omdb_data = omdb_result["omdb_data"]
                    poster_bytes = omdb_result["poster_bytes"]

                    result_movies.append(
                        {
                            "title": omdb_data.get("Title"),
                            "year": int(omdb_data.get("Year", 0))
                            if omdb_data.get("Year", "0").isdigit()
                            else omdb_data.get("Year"),
                            "category": category,
                            "poster_base64": _get_poster_base64(poster_bytes),
                            "plot": omdb_data.get("Plot"),
                            "genre": omdb_data.get("Genre"),
                            "imdb_rating": float(omdb_data.get("imdbRating", 0))
                            if omdb_data.get("imdbRating", "0")
                            .replace(".", "")
                            .isdigit()
                            else None,
                            "metadata_source": "omdb",
                        }
                    )
                else:
                    _save_to_local_content(title, year, category)

                    result_movies.append(
                        {
                            "title": title,
                            "year": year,
                            "category": category,
                            "poster_base64": None,
                            "plot": None,
                            "genre": category.capitalize(),
                            "imdb_rating": None,
                            "metadata_source": "local",
                        }
                    )

        return jsonify({"movies": result_movies})

    except Exception as e:
        logger.error(f"Error en get_movies: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
