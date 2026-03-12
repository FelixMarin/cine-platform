"""
Adaptador de entrada - Rutas de catálogo con base de datos
Blueprint para /api/omdb, /api/catalog y endpoints relacionados
"""

import os
import io
from flask import Blueprint, jsonify, request, send_file
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
)
from src.adapters.outgoing.services.omdb.cached_client import get_omdb_service_cached
from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

catalog_db_bp = Blueprint("catalog_db", __name__, url_prefix="/api")

_catalog_repo = None
_omdb_service = None


def _get_catalog_repo():
    global _catalog_repo
    if _catalog_repo is None:
        _catalog_repo = get_catalog_repository()
    return _catalog_repo


def _get_omdb_service():
    global _omdb_service
    if _omdb_service is None:
        _omdb_service = get_omdb_service_cached()
    return _omdb_service


@catalog_db_bp.route("/omdb/search", methods=["GET"])
def omdb_search():
    """Búsqueda en OMDB con caché"""
    query = request.args.get("q", "")
    limit = request.args.get("limit", 10, type=int)

    if not query:
        return jsonify({"error": "Query no proporcionada"}), 400

    try:
        omdb_service = _get_omdb_service()
        results = omdb_service.search_movies_cached(query, limit=limit)
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        logger.error(f"Error en OMDB search: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/omdb/lookup", methods=["GET"])
def omdb_lookup():
    """Obtiene detalles de una película/serie por IMDB ID"""
    imdb_id = request.args.get("imdb_id", "")
    force_refresh = request.args.get("refresh", "false").lower() == "true"

    if not imdb_id:
        return jsonify({"error": "imdb_id no proporcionado"}), 400

    try:
        omdb_service = _get_omdb_service()
        result = omdb_service.get_movie_by_imdb_id(imdb_id, force_refresh=force_refresh)

        if not result:
            return jsonify({"error": "Contenido no encontrado"}), 404

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error en OMDB lookup: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/omdb/poster/<imdb_id>", methods=["GET"])
def get_omdb_poster(imdb_id):
    """Obtiene el póster de una película desde la BBDD"""
    try:
        poster_bytes = _get_omdb_service().get_poster_image(imdb_id)

        if not poster_bytes:
            return jsonify({"error": "Póster no encontrado"}), 404

        return send_file(
            io.BytesIO(poster_bytes),
            mimetype="image/jpeg",
            as_attachment=False,
            download_name=f"{imdb_id}.jpg",
        )
    except Exception as e:
        logger.error(f"Error obteniendo póster: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/catalog/movies", methods=["GET"])
def get_catalog_movies():
    """Lista películas del catálogo local"""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    repo = None
    try:
        repo = _get_catalog_repo()
        movies = repo.list_movies(limit=limit, offset=offset)
        return jsonify(
            {
                "movies": [m.to_dict() for m in movies],
                "count": len(movies),
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        logger.error(f"Error listando películas: {e}")
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


@catalog_db_bp.route("/catalog/series", methods=["GET"])
def get_catalog_series():
    """Lista series del catálogo local"""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    repo = None
    try:
        repo = _get_catalog_repo()
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
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


@catalog_db_bp.route("/catalog", methods=["POST"])
@require_auth
def create_catalog_entry():
    """Añade contenido manual al catálogo (sin imdb_id)"""
    data = request.json

    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400

    repo = None
    try:
        repo = _get_catalog_repo()
        content = repo.create_local_content(data)
        return jsonify(content.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creando entrada: {e}")
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


@catalog_db_bp.route("/catalog/<int:content_id>", methods=["PUT"])
@require_auth
def update_catalog_entry(content_id):
    """Actualiza metadata de contenido"""
    data = request.json

    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400

    repo = None
    try:
        repo = _get_catalog_repo()
        content = repo.update_local_content(content_id, data)

        if not content:
            return jsonify({"error": "Contenido no encontrado"}), 404

        return jsonify(content.to_dict())
    except Exception as e:
        logger.error(f"Error actualizando entrada: {e}")
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


@catalog_db_bp.route("/catalog/<int:content_id>", methods=["DELETE"])
@require_auth
def delete_catalog_entry(content_id):
    """Elimina contenido del catálogo"""
    repo = None
    try:
        repo = _get_catalog_repo()
        success = repo.delete_local_content(content_id)

        if not success:
            return jsonify({"error": "Contenido no encontrado"}), 404

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error eliminando entrada: {e}")
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


@catalog_db_bp.route("/catalog/<int:content_id>", methods=["GET"])
def get_catalog_entry(content_id):
    """Obtiene una entrada del catálogo por ID"""
    repo = None
    try:
        repo = _get_catalog_repo()
        content = repo.get_local_content_by_id(content_id)

        if not content:
            return jsonify({"error": "Contenido no encontrado"}), 404

        return jsonify(content.to_dict(include_image=True))
    except Exception as e:
        logger.error(f"Error obteniendo entrada: {e}")
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


@catalog_db_bp.route("/migrate/localstorage", methods=["POST"])
@require_auth
def migrate_localstorage():
    """Migra datos desde localStorage del frontend"""
    data = request.json

    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400

    repo = None
    try:
        repo = _get_catalog_repo()
        result = repo.migrate_local_storage_data(data)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.error(f"Error en migración: {e}")
        if repo:
            repo.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if repo:
            repo.close()


def init_catalog_db_routes(state=None):
    """Inicializa las rutas del catálogo de base de datos"""
    logger.info("[CATALOG_DB] Rutas de catálogo con BBDD inicializadas")


catalog_db_bp.record_once(init_catalog_db_routes)
