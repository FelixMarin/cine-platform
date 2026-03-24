"""
Adaptador de entrada - Rutas de catálogo
Blueprint para /api/movies y endpoints relacionados
"""

import unicodedata
import os
from flask import Blueprint, jsonify, request
from src.adapters.entry.web.middleware.auth_middleware import require_auth

from src.core.use_cases.catalog import (
    ListMoviesUseCase,
    ListSeriesUseCase,
    SearchUseCase,
)

from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


catalog_bp = Blueprint("catalog", __name__, url_prefix="")

# Casos de uso inyectados
_list_movies_use_case = None
_list_series_use_case = None
_search_use_case = None


def init_catalog_routes(
    list_movies_use_case: ListMoviesUseCase = None,
    list_series_use_case: ListSeriesUseCase = None,
    search_use_case: SearchUseCase = None,
):
    """Inicializa los casos de uso para las rutas de catálogo"""
    global _list_movies_use_case, _list_series_use_case, _search_use_case
    _list_movies_use_case = list_movies_use_case
    _list_series_use_case = list_series_use_case
    _search_use_case = search_use_case


@catalog_bp.route("/api/categories", methods=["GET"])
def get_categories():
    """Obtiene todas las categorías con películas y series"""
    try:
        # Obtener películas
        movies = _list_movies_use_case.execute() if _list_movies_use_case else []

        # Obtener series
        series = _list_series_use_case.execute() if _list_series_use_case else []

        return jsonify({"movies": movies, "series": series})
    except Exception as e:
        import logging

        logging.error(f"Error getting categories: {e}")
        return jsonify({"error": str(e)}), 500



@catalog_bp.route("/api/search", methods=["GET"])
def search_content():
    """Busca contenido en el catálogo"""
    global _search_use_case

    if _search_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        query = request.args.get("q", "")

        if not query:
            return jsonify({"error": "Query no proporcionada"}), 400

        results = _search_use_case.execute(query)

        return jsonify(normalize_dict(results))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@catalog_bp.route("/api/movie-thumbnail/<filename>", methods=["GET"])
def get_movie_thumbnail(filename):
    """Obtiene el thumbnail de una película"""
    # Este endpoint se manejará en otro archivo (thumbnails)
    return jsonify({"error": "Endpoint no implementado en este blueprint"}), 501


@catalog_bp.route("/api/movie-thumbnail", methods=["GET"])
def get_movie_thumbnail_by_title():
    """
    Obtiene el thumbnail de una película por título (query param).

    Flujo (prioridad de fuentes):
        1. Base de datos (poster_image de omdb_entries) - FUENTE PRIMARIA
        2. Base de datos (poster_image de local_content) - FALLBACK PARA CONTENIDO SIN IMDB
        3. OMDB API + guardar en BD (si no hay en BD)
        4. Sistema de archivos local (thumbnails manuales) - FALLBACK

    El servicio DatabaseThumbnailService es la fuente primaria que busca
    directamente en el campo poster_image de las tablas omdb_entries y local_content.
    """
    import logging
    import io
    from flask import send_file

    logger = logging.getLogger(__name__)

    # Importar servicios de thumbnails
    from src.adapters.config.dependencies import get_database_thumbnail_service
    from src.adapters.outgoing.services.omdb.thumbnail_provider import (
        get_omdb_thumbnail_provider,
    )
    from src.adapters.outgoing.services.thumbnails.local_search import (
        get_local_thumbnail_search,
    )

    # Obtener servicios
    db_thumbnail_service = get_database_thumbnail_service()
    omdb_provider = get_omdb_thumbnail_provider()
    local_search = get_local_thumbnail_search()

    # === 1. Validar parámetros ===
    title = request.args.get("title")
    year = request.args.get("year")
    filename = request.args.get("filename")

    if not title:
        return jsonify({"error": "Titulo no proporcionado"}), 400

    logger.info(f"Buscando thumbnail para: [{title}] año=[{year}]")

    # === 2. FUENTE PRIMARIA: Buscar en base de datos (poster_image) ===
    thumbnail_data = db_thumbnail_service.get_thumbnail_from_db(title, year)

    if thumbnail_data:
        return send_file(
            io.BytesIO(thumbnail_data),
            mimetype="image/jpeg",
            as_attachment=False,
            max_age=86400,  # Cache 24h en navegador
        )

    # === 3. Si no hay en BD, intentar obtener de OMDB (y guardar en BD) ===
    logger.info(f"DB: No se encontró en BD, intentando OMDB para [{title}]")
    thumbnail_data = omdb_provider.fetch_thumbnail_data(title, year)

    if thumbnail_data:
        logger.info(f"OMDB: Poster obtenido para [{title}] y guardado en BD")
        return send_file(
            io.BytesIO(thumbnail_data),
            mimetype="image/jpeg",
            as_attachment=False,
            max_age=86400,  # Cache 24h en navegador
        )

    # === 4. FALLBACK FINAL: Buscar en sistema de archivos local ===
    logger.info(f"OMDB: No se encontró, buscando thumbnail local para [{title}]")
    local_thumbnail = local_search.search_local_thumbnail(title, filename)

    if local_thumbnail:
        return jsonify({"thumbnail": local_thumbnail})

    # === 5. Si no se encontró en ningún lado, devolver 404 ===
    logger.info(f"❌ Sin datos: thumbnail no encontrado para [{title}]")
    return jsonify({"error": "Thumbnail no encontrado"}), 404


@catalog_bp.route("/api/serie-poster", methods=["GET"])
def get_serie_poster():
    """Obtiene el póster de una serie por nombre"""
    from src.adapters.config.dependencies import get_metadata_service

    name = request.args.get("name")

    if not name:
        return jsonify({"error": "Nombre de serie no proporcionado"}), 400

    metadata_service = get_metadata_service()
    if not metadata_service:
        return jsonify({"error": "Servicio de metadatos no disponible"}), 500

    try:
        poster = metadata_service.get_serie_poster(name)
        if poster:
            return jsonify({"poster": poster})
        return jsonify({"error": "Póster no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
