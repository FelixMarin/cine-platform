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
    get_catalog_repository_session,
)
from src.adapters.outgoing.services.omdb.cached_client import get_omdb_service_cached
from src.adapters.entry.web.routes.catalog_sync import _clean_omdb_value
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

    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
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
                existing = repo.list_local_content(content_type="series", limit=1, offset=0)
                if len(existing) == 0:
                    logger.info("No hay series en el catálogo. Ejecutando sincronización automática...")
                    
                    # Escanear series del filesystem
                    from src.adapters.entry.web.routes.catalog_sync import _scan_series_from_filesystem, _get_omdb_service
                    series_on_disk = _scan_series_from_filesystem()
                    
                    if series_on_disk:
                        omdb_service = _get_omdb_service()
                        
                        db_series = repo.list_local_content(content_type="series", limit=10000, offset=0)
                        db_series_by_title = {s.title: s for s in db_series if s.title}
                        
                        added_series = 0
                        for serie_name, serie_data in series_on_disk.items():
                            if serie_name in db_series_by_title:
                                continue
                            
                            try:
                                search_results = omdb_service.search_series_cached(serie_name, limit=5)
                                imdb_id = None
                                
                                # Obtener año de la serie si está disponible
                                serie_year = serie_data.get("year")

                                # Filtrar por título Y año exacto para evitar insertar series incorrectas
                                for result in search_results:
                                    result_title = result.get('title', '')
                                    result_year = result.get('year')
                                    # Comparar títulos de forma más flexible
                                    title_match = serie_name.lower() in result_title.lower() or result_title.lower() in serie_name.lower()
                                    year_match = serie_year and result_year and str(serie_year) == str(result_year)
                                    
                                    if title_match and year_match:
                                        imdb_id = result.get('imdb_id') or result.get('imdbID')
                                        break
                                
                                # Si no hay coincidencia exacta, NO insertar
                                if not imdb_id:
                                    logger.warning(
                                        f"No se encontró coincidencia exacta para serie: {serie_name} ({serie_year})"
                                    )
                                
                                if imdb_id:
                                    omdb_data = omdb_service.get_serie_by_imdb_id_raw(imdb_id)
                                    if omdb_data:
                                        total_seasons = omdb_data.get('totalSeasons') or serie_data['seasons_found']
                                        
                                        poster_bytes = None
                                        poster_url = omdb_data.get('Poster')
                                        if poster_url and poster_url != 'N/A':
                                            try:
                                                import requests
                                                poster_response = requests.get(poster_url, timeout=10)
                                                if poster_response.status_code == 200:
                                                    poster_bytes = poster_response.content
                                            except:
                                                pass
                                        
                                        content_data = {
                                            'imdb_id': omdb_data.get('imdbID'),
                                            'title': omdb_data.get('Title') or serie_name,
                                            'year': omdb_data.get('Year'),
                                            'rated': omdb_data.get('Rated'),
                                            'released': omdb_data.get('Released'),
                                            'runtime': omdb_data.get('Runtime'),
                                            'genre': omdb_data.get('Genre'),
                                            'director': omdb_data.get('Director'),
                                            'writer': omdb_data.get('Writer'),
                                            'actors': omdb_data.get('Actors'),
                                            'plot': omdb_data.get('Plot'),
                                            'language': omdb_data.get('Language'),
                                            'country': omdb_data.get('Country'),
                                            'awards': _clean_omdb_value(omdb_data.get('Awards')),
                                            'poster_url': _clean_omdb_value(poster_url),
                                            'poster_image': poster_bytes,
                                            'metascore': _clean_omdb_value(omdb_data.get('Metascore'), 'integer'),
                                            'imdb_rating': _clean_omdb_value(omdb_data.get('imdbRating'), 'float'),
                                            'imdb_votes': _clean_omdb_value(omdb_data.get('imdbVotes')),
                                            'type': 'series',
                                            'total_seasons': _clean_omdb_value(total_seasons, 'integer'),
                                            'box_office': _clean_omdb_value(omdb_data.get('BoxOffice')),
                                            'production': _clean_omdb_value(omdb_data.get('Production')),
                                            'website': _clean_omdb_value(omdb_data.get('Website')),
                                            'dvd_release': _clean_omdb_value(omdb_data.get('DVD')),
                                            'ratings': _clean_omdb_value(omdb_data.get('Ratings')),
                                            'file_path': serie_data['path'],
                                            'full_response': omdb_data,
                                        }
                                        repo.create_local_content(content_data)
                                        added_series += 1
                                        logger.info(f"Serie añadida automáticamente: {content_data['title']}")
                            except Exception as e:
                                logger.error(f"Error sincronizando serie {serie_name}: {e}")
                        
                        if added_series > 0:
                            logger.info(f"Sincronización automática completada: {added_series} series añadidas")
            
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
            content = repo.get_local_content_by_id(content_id)

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




# Endpoints adicionales para series
@catalog_db_bp.route("/series/<int:serie_id>/seasons", methods=["GET"])
def get_serie_seasons(serie_id):
    """Devuelve las temporadas disponibles de una serie"""
    import re
    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            serie = repo.get_local_content_by_id(serie_id)
            
            if not serie or serie.type != 'series':
                return jsonify({"error": "Serie no encontrada"}), 404
            
            serie_path = serie.file_path
            if not serie_path or not os.path.exists(serie_path):
                return jsonify({"error": "Ruta de serie no valida"}), 404
            
            season_pattern = re.compile(r'^S(\d+)$', re.IGNORECASE)
            seasons = []
            
            try:
                for item in os.listdir(serie_path):
                    item_path = os.path.join(serie_path, item)
                    if os.path.isdir(item_path):
                        match = season_pattern.match(item)
                        if match:
                            seasons.append({
                                "season": int(match.group(1)),
                                "folder": item
                            })
            except Exception as e:
                logger.error(f"Error leyendo carpetas de temporada: {e}")
                return jsonify({"error": str(e)}), 500
            
            seasons.sort(key=lambda x: x['season'])
            return jsonify({
                "serie_id": serie_id,
                "serie_title": serie.title,
                "seasons": seasons
            })
    except Exception as e:
        logger.error(f"Error obteniendo temporadas: {e}")
        return jsonify({"error": str(e)}), 500


@catalog_db_bp.route("/series/<int:serie_id>/season/<int:season>/episodes", methods=["GET"])
def get_season_episodes(serie_id, season):
    """Devuelve los episodios de una temporada"""
    import re
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
    
    try:
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            serie = repo.get_local_content_by_id(serie_id)
            
            if not serie or serie.type != 'series':
                return jsonify({"error": "Serie no encontrada"}), 404
            
            serie_path = serie.file_path
            if not serie_path or not os.path.exists(serie_path):
                return jsonify({"error": "Ruta de serie no valida"}), 404
            
            season_folder = "S{:02d}".format(season)
            season_path = os.path.join(serie_path, season_folder)
            
            if not os.path.exists(season_path):
                return jsonify({
                    "serie_id": serie_id,
                    "season": season,
                    "episodes": []
                })
            
            serie_name_base = serie.title.replace(' ', '-')
            pattern_str = serie_name_base + "-S{:02d}E(\d+)-serie".format(season)
            episode_pattern = re.compile(pattern_str, re.IGNORECASE)
            
            episodes = []
            try:
                for f in os.listdir(season_path):
                    file_path = os.path.join(season_path, f)
                    if not os.path.isfile(file_path):
                        continue
                    
                    ext = os.path.splitext(f)[1].lower()
                    if ext not in valid_extensions:
                        continue
                    
                    match = episode_pattern.search(f)
                    if match:
                        episodes.append({
                            "episode": int(match.group(1)),
                            "filename": f,
                            "file_path": file_path
                        })
            except Exception as e:
                logger.error(f"Error leyendo episodios: {e}")
                return jsonify({"error": str(e)}), 500
            
            episodes.sort(key=lambda x: x['episode'])
            return jsonify({
                "serie_id": serie_id,
                "serie_title": serie.title,
                "season": season,
                "episodes": episodes
            })
    except Exception as e:
        logger.error(f"Error obteniendo episodios: {e}")
        return jsonify({"error": str(e)}), 500



catalog_db_bp.record_once(init_catalog_db_routes)
