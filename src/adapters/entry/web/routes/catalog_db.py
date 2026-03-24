"""
Adaptador de entrada - Rutas de catálogo con base de datos
Blueprint para /api/omdb, /api/catalog y endpoints relacionados
"""

import os
import io
import re
import base64
from flask import Blueprint, jsonify, request, send_file
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)
from src.adapters.outgoing.services.omdb.cached_client import get_omdb_service_cached
from src.adapters.entry.web.routes.catalog_sync import _clean_omdb_value
from src.infrastructure.models.catalog import OmdbEntry, LocalContent
from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

catalog_db_bp = Blueprint("catalog_db", __name__, url_prefix="/api")

# Ya no necesitamos singleton - cada request usa su propia sesión
_omdb_service = None


def _get_omdb_service():
    global _omdb_service
    if _omdb_service is None:
        _omdb_service = get_omdb_service_cached()
    return _omdb_service


def _bytes_to_base64(data):
    """Convierte bytes a string base64 para JSON"""
    if data is None:
        return None
    try:
        return base64.b64encode(data).decode("utf-8")
    except Exception:
        return None


def _normalize_title(s):
    """Normaliza título para comparación"""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())


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
    auto_sync = request.args.get("auto_sync", "true").lower() == "true"

    try:
        # Escanear películas del FS
        from src.adapters.entry.web.routes.catalog_movies import (
            _scan_movies_from_filesystem,
        )

        movies_fs = _scan_movies_from_filesystem()
        logger.info(f"Películas en FS: {len(movies_fs)}")

        if not movies_fs:
            return jsonify({"movies": [], "count": 0, "limit": limit, "offset": offset})

        result_movies = []

        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)

            # Obtener todas las películas de omdb_entries
            all_omdb = repo.list_omdb_entries(
                content_type="movie", limit=10000, offset=0
            )
            omdb_by_key = {}
            for entry in all_omdb:
                if entry.title and entry.year:
                    key = (entry.title.lower(), str(entry.year))
                    omdb_by_key[key] = entry

            # Obtener todas las películas de local_content
            all_local = repo.list_local_content(
                content_type="movie", limit=10000, offset=0
            )
            local_by_key = {}
            for entry in all_local:
                if entry.title and entry.year:
                    key = (entry.title.lower(), str(entry.year))
                    local_by_key[key] = entry

            # Sincronización automática si auto_sync está activado
            if auto_sync:
                from src.adapters.entry.web.routes.catalog_sync import _get_omdb_service

                omdb_service = _get_omdb_service()

                for movie in movies_fs:
                    title = movie.get("title", "")
                    year = movie.get("year")

                    if not title:
                        continue

                    key = (title.lower(), str(year) if year else None)

                    if key in omdb_by_key or key in local_by_key:
                        continue

                    omdb_data = omdb_service.get_movie_metadata(title, year=year)

                    if omdb_data and omdb_data.get("Response") != "False":
                        repo.create_or_update_omdb_entry(omdb_data)
                        logger.info(
                            f"Añadida película desde OMDB: {omdb_data.get('Title')}"
                        )
                    else:
                        content_data = {
                            "title": title,
                            "year": str(year) if year else None,
                            "type": "movie",
                            "file_path": movie.get("file_path"),
                        }
                        repo.create_local_content(content_data)
                        logger.info(f"Añadida película sin IMDB: {title}")

                # Recargar después de sync
                all_omdb = repo.list_omdb_entries(
                    content_type="movie", limit=10000, offset=0
                )
                omdb_by_key = {}
                for entry in all_omdb:
                    if entry.title and entry.year:
                        key = (entry.title.lower(), str(entry.year))
                        omdb_by_key[key] = entry

                all_local = repo.list_local_content(
                    content_type="movie", limit=10000, offset=0
                )
                local_by_key = {}
                for entry in all_local:
                    if entry.title and entry.year:
                        key = (entry.title.lower(), str(entry.year))
                        local_by_key[key] = entry

            # Construir resultado
            for movie in movies_fs:
                title = movie.get("title", "")
                year = movie.get("year")

                if not title:
                    continue

                key = (title.lower(), str(year) if year else None)

                if key in omdb_by_key:
                    entry = omdb_by_key[key]
                    result_movies.append(
                        {
                            "title": entry.title,
                            "year": entry.year,
                            "genre": entry.genre,
                            "plot": entry.plot,
                            "poster_url": entry.poster_url,
                            "poster_base64": _bytes_to_base64(entry.poster_image)
                            if entry.poster_image
                            else None,
                            "imdb_rating": entry.imdb_rating,
                            "director": entry.director,
                            "actors": entry.actors,
                            "file_path": movie.get("file_path"),
                            "metadata_source": "omdb",
                        }
                    )
                    continue

                if key in local_by_key:
                    entry = local_by_key[key]
                    result_movies.append(
                        {
                            "title": entry.title,
                            "year": entry.year,
                            "genre": entry.genre,
                            "plot": entry.plot,
                            "poster_url": entry.poster_url,
                            "poster_base64": _bytes_to_base64(entry.poster_image)
                            if entry.poster_image
                            else None,
                            "imdb_rating": entry.imdb_rating,
                            "director": entry.director,
                            "actors": entry.actors,
                            "file_path": movie.get("file_path"),
                            "metadata_source": "local",
                        }
                    )
                    continue

                # Datos del FS
                result_movies.append(
                    {
                        "title": title,
                        "year": year,
                        "genre": movie.get("category", "").capitalize(),
                        "plot": None,
                        "poster_url": None,
                        "poster_base64": None,
                        "imdb_rating": None,
                        "director": None,
                        "actors": None,
                        "file_path": movie.get("file_path"),
                        "metadata_source": "filesystem",
                    }
                )

            total = len(result_movies)
            paginated = result_movies[offset : offset + limit]

            return jsonify(
                {"movies": paginated, "count": total, "limit": limit, "offset": offset}
            )

    except Exception as e:
        logger.error(f"Error listando películas: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/catalog/series", methods=["GET"])
def get_catalog_series():
    """Lista series del catálogo local"""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    auto_sync = request.args.get("auto_sync", "true").lower() == "true"

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)

            # Sincronización automática si no hay series y auto_sync está activado
            if auto_sync:
                existing = repo.list_local_content(
                    content_type="series", limit=1, offset=0
                )
                if len(existing) == 0:
                    logger.info(
                        "No hay series en el catálogo. Ejecutando sincronización automática..."
                    )

                    # Escanear series del filesystem
                    from src.adapters.entry.web.routes.catalog_sync import (
                        _scan_series_from_filesystem,
                        _get_omdb_service,
                    )

                    series_on_disk = _scan_series_from_filesystem()

                    if series_on_disk:
                        omdb_service = _get_omdb_service()

                        db_series = repo.list_local_content(
                            content_type="series", limit=10000, offset=0
                        )
                        db_series_by_title = {s.title: s for s in db_series if s.title}

                        added_series = 0
                        for serie_name, serie_data in series_on_disk.items():
                            if serie_name in db_series_by_title:
                                continue

                            try:
                                omdb_data = omdb_service.get_serie_metadata(serie_name)

                                if omdb_data and omdb_data.get("Response") != "False":
                                    total_seasons = (
                                        omdb_data.get("totalSeasons")
                                        or serie_data["seasons_found"]
                                    )

                                    poster_bytes = None
                                    poster_url = omdb_data.get("Poster")
                                    if poster_url and poster_url != "N/A":
                                        try:
                                            import requests

                                            poster_response = requests.get(
                                                poster_url, timeout=10
                                            )
                                            if poster_response.status_code == 200:
                                                poster_bytes = poster_response.content
                                        except:
                                            pass

                                    repo.create_or_update_omdb_entry(
                                        omdb_data, poster_bytes
                                    )
                                    added_series += 1
                                    logger.info(
                                        f"Serie añadida automáticamente: {omdb_data.get('Title')}"
                                    )
                                else:
                                    logger.warning(
                                        f"No se encontró serie en OMDB: {serie_name}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Error sincronizando serie {serie_name}: {e}"
                                )

                        if added_series > 0:
                            logger.info(
                                f"Sincronización automática completada: {added_series} series añadidas"
                            )

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


@catalog_db_bp.route("/catalog", methods=["POST"])
@require_auth
def create_catalog_entry():
    """Añade contenido manual al catálogo (sin imdb_id)"""
    data = request.json

    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            content = repo.create_local_content(data)
            return jsonify(content.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creando entrada: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/catalog/<int:content_id>", methods=["PUT"])
@require_auth
def update_catalog_entry(content_id):
    """Actualiza metadata de contenido"""
    data = request.json

    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            content = repo.update_local_content(content_id, data)

            if not content:
                return jsonify({"error": "Contenido no encontrado"}), 404

            return jsonify(content.to_dict())
    except Exception as e:
        logger.error(f"Error actualizando entrada: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/catalog/<int:content_id>", methods=["DELETE"])
@require_auth
def delete_catalog_entry(content_id):
    """Elimina contenido del catálogo"""
    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            success = repo.delete_local_content(content_id)

            if not success:
                return jsonify({"error": "Contenido no encontrado"}), 404

            return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error eliminando entrada: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/catalog/<int:content_id>", methods=["GET"])
def get_catalog_entry(content_id):
    """Obtiene una entrada del catálogo por ID"""
    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            # Primero intentar en local_content
            content = repo.get_local_content_by_id(content_id)

            if not content:
                # Si no está, buscar en omdb_entries
                content = db.query(OmdbEntry).filter(OmdbEntry.id == content_id).first()
                if not content:
                    return jsonify({"error": "Contenido no encontrado"}), 404

            return jsonify(content.to_dict(include_image=True))
    except Exception as e:
        logger.error(f"Error obteniendo entrada: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/migrate/localstorage", methods=["POST"])
@require_auth
def migrate_localstorage():
    """Migra datos desde localStorage del frontend"""
    data = request.json

    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            result = repo.migrate_local_storage_data(data)
            return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.error(f"Error en migración: {e}")
        return jsonify({"error": str(e)}), 500


def init_catalog_db_routes(state=None):
    """Inicializa las rutas del catálogo de base de datos"""
    logger.info("[CATALOG_DB] Rutas de catálogo con BBDD inicializadas")




catalog_db_bp.record_once(init_catalog_db_routes)
