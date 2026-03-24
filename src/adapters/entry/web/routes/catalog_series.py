"""
Adaptador de entrada - Rutas de catálogo de series
Blueprint para /api/series con metadata de OMDB
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

catalog_series_bp = Blueprint("catalog_series", __name__, url_prefix="/api")

SERIES_BASE_PATH = "/mnt/DATA_2TB/audiovisual/series"
VALID_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".flv", ".wmv"}


def _clean_unicode(text: str) -> str:
    """Limpia caracteres Unicode problemáticos"""
    if not text:
        return text
    surrogate_map = {
        "\udce1": "á",
        "\udce9": "é",
        "\udced": "í",
        "\udcf3": "ó",
        "\udcfa": "ú",
        "\udcc1": "Á",
        "\udcc9": "É",
        "\udccd": "Í",
        "\udcf3": "Ó",
        "\udcfa": "Ú",
        "\udcf1": "ñ",
        "\udcd1": "Ñ",
    }
    for surrogate, char in surrogate_map.items():
        text = text.replace(surrogate, char)
    import unicodedata

    return unicodedata.normalize("NFC", text)


def _scan_series_from_filesystem() -> dict:
    """Escanea el sistema de archivos para obtener series."""
    series_data = {}

    if not os.path.exists(SERIES_BASE_PATH):
        logger.warning(f"La carpeta base de series no existe: {SERIES_BASE_PATH}")
        return series_data

    for item in os.listdir(SERIES_BASE_PATH):
        item_path = os.path.join(SERIES_BASE_PATH, item)

        if not os.path.isdir(item_path):
            continue

        serie_name = _clean_unicode(item.replace(".", " ").strip())

        if serie_name not in series_data:
            series_data[serie_name] = {
                "title": serie_name,
                "path": item_path,
                "seasons": set(),
            }

        for subitem in os.listdir(item_path):
            subitem_path = os.path.join(item_path, subitem)

            if not os.path.isdir(subitem_path):
                continue

            season_match = re.search(r"[Ss](\d+)", subitem)
            if season_match:
                season_num = int(season_match.group(1))
                series_data[serie_name]["seasons"].add(season_num)

    for serie_name in series_data:
        series_data[serie_name]["seasons"] = sorted(
            list(series_data[serie_name]["seasons"])
        )
        series_data[serie_name]["total_seasons"] = len(
            series_data[serie_name]["seasons"]
        )

    return series_data


def _get_omdb_series(db: CatalogRepository, title: str):
    """Busca en omdb_entries por título EXACTO + type='series'"""
    from src.infrastructure.models.catalog import OmdbEntry

    db_session = db._get_db()
    return (
        db_session.query(OmdbEntry)
        .filter(OmdbEntry.title == title, OmdbEntry.type == "series")
        .first()
    )


def _get_local_series(db: CatalogRepository, title: str):
    """Busca en local_content por título EXACTO + type='series'"""
    from src.infrastructure.models.catalog import LocalContent

    db_session = db._get_db()
    return (
        db_session.query(LocalContent)
        .filter(LocalContent.title == title, LocalContent.type == "series")
        .first()
    )


def _fetch_and_save_series_from_omdb(title: str) -> dict:
    """Consulta OMDB API para series y guarda el resultado."""
    api_key = settings.OMDB_API_KEY
    if not api_key:
        logger.warning("OMDB_API_KEY no configurada")
        return None

    omdb_service = OMDBMetadataService(api_key)

    search_results = omdb_service.search_series(title)

    if not search_results:
        return None

    exact_matches = []
    for result in search_results:
        result_title = result.get("Title", "").strip()
        if result_title.lower() == title.lower():
            exact_matches.append(result)

    if len(exact_matches) >= 1:
        exact_match = exact_matches[0]

        full_data = omdb_service.get_serie_metadata(exact_match["Title"])

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

            try:
                with get_catalog_repository() as db:
                    db.create_or_update_omdb_entry(full_data, poster_bytes)
            except Exception as e:
                logger.warning(f"Error guardando en BD: {e}")

            return {"omdb_data": full_data, "poster_bytes": poster_bytes}

    return None


def _save_to_local_series(title: str):
    """Guarda en local_content cuando no hay coincidencia exacta en OMDB"""
    try:
        with get_catalog_repository() as db:
            db.create_local_content({"title": title, "type": "series"})
    except Exception as e:
        logger.warning(f"Error guardando en local_content: {e}")


def _get_poster_base64(poster_bytes) -> str:
    """Convierte bytes de imagen a base64 data URI"""
    if not poster_bytes:
        return None
    try:
        b64 = base64.b64encode(poster_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None


def _safe_float(value):
    """Convierte a float de forma segura"""
    if value is None:
        return None
    try:
        return float(value)
    except:
        return None


