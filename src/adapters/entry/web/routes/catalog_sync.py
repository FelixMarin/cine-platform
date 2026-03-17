"""
Funciones de sincronización del catálogo con el sistema de archivos
"""

import os
import re
import logging
from typing import Optional, Dict, List
from flask import Blueprint, jsonify, request
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)
from src.adapters.outgoing.services.omdb.cached_client import get_omdb_service_cached
from src.infrastructure.config.settings import settings


def _invalidate_movie_repository_cache():
    """
    Invalida la caché del repositorio de películas (FilesystemMovieRepository).
    Esto asegura que después de sincronizar, el catálogo se refresque con los nuevos datos.
    """
    try:
        from src.adapters.config.dependencies import get_movie_repository

        repo = get_movie_repository()
        if repo and hasattr(repo, "invalidate_cache"):
            repo.invalidate_cache()
            logger.info("✅ Caché de FilesystemMovieRepository invalidada")

        cache_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../outgoing/repositories/filesystem/.movie_index_cache.json",
        )
        cache_file = os.path.normpath(cache_file)

        if os.path.exists(cache_file):
            os.remove(cache_file)
            logger.info(f"✅ Archivo de caché eliminado: {cache_file}")
        else:
            logger.info(f"ℹ️ Archivo de caché no existe: {cache_file}")
    except Exception as e:
        logger.warning(f"⚠️ Error invalidando caché: {e}")


logger = logging.getLogger(__name__)

# Rutas de archivos
MOVIES_FOLDER = getattr(settings, "MOVIES_FOLDER", "/mnt/DATA_2TB/audiovisual")
MOVIES_BASE_PATH = getattr(
    settings, "MOVIES_BASE_PATH", "/mnt/DATA_2TB/audiovisual/mkv"
)
SERIES_FOLDER = getattr(settings, "SERIES_FOLDER", "/mnt/DATA_2TB/audiovisual/series")

_omdb_service = None


def _clean_omdb_value(value, field_type="string"):
    """
    Convierte valores 'N/A' de OMDB a None para evitar errores de tipo en la BD.

    Args:
        value: El valor recibido de OMDB
        field_type: Tipo de campo ('string', 'integer', 'float')

    Returns:
        El valor limpio o None si es 'N/A' o no es convertible
    """
    # Normalizar el valor
    if value is None:
        return None

    # Convertir a string para comparar
    value_str = str(value).strip()

    # Si es 'N/A', devolver None
    if value_str.upper() in ("N/A", "NA", ""):
        return None

    # Convertir según el tipo de campo
    if field_type == "integer":
        try:
            return int(value_str)
        except (ValueError, TypeError):
            return None

    if field_type == "float":
        try:
            # Limpiar el valor (algunos ratings vienen como "8.5/10")
            clean_value = value_str.split("/")[0]
            return float(clean_value)
        except (ValueError, TypeError):
            return None

    # Para strings, devolver el valor original si no es 'N/A'
    return value


def _get_omdb_service():
    global _omdb_service
    if _omdb_service is None:
        _omdb_service = get_omdb_service_cached()
    return _omdb_service


def _scan_movies_from_filesystem():
    """Escanea películas del sistema de archivos"""
    movies = {}
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

    base_path = MOVIES_BASE_PATH if os.path.exists(MOVIES_BASE_PATH) else MOVIES_FOLDER

    if not os.path.exists(base_path):
        logger.warning(f"Carpeta de películas no existe: {base_path}")
        return movies

    try:
        for category in os.listdir(base_path):
            category_path = os.path.join(base_path, category)
            if not os.path.isdir(category_path):
                continue

            for filename in os.listdir(category_path):
                file_path = os.path.join(category_path, filename)
                if not os.path.isfile(file_path):
                    continue

                ext = os.path.splitext(filename)[1].lower()
                if ext not in valid_extensions:
                    continue

                title, year = _parse_filename(filename)
                if not title:
                    continue

                movies[file_path] = {
                    "title": title,
                    "year": year,
                    "file_path": file_path,
                    "category": category,
                    "filename": filename,
                }
    except Exception as e:
        logger.error(f"Error escaneando películas: {e}")

    logger.info(f"Escaneadas {len(movies)} películas del sistema de archivos")
    return movies


def _scan_series_from_filesystem():
    """
    Escanea series del sistema de archivos de forma eficiente.

    Modelo eficiente: UNA entrada por serie, NO por episodio.
    La ruta del episodio se construye en tiempo de reproducción.

    Estructura esperada:
    SERIES_FOLDER/
        Serie Name/
            S01/
                Serie-S01E01.mkv
                Serie-S01E02.mkv
            S02/
                Serie-S02E01.mkv

    Returns:
        dict: Diccionario con estructura por serie:
        {
            "Serie Name": {
                "title": "Serie Name",
                "path": "/path/to/Serie Name",
                "seasons_found": 3,
                "episodes_found": 24,
                "has_valid_structure": True
            }
        }
    """
    series = {}
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

    # Patrones para detectar carpetas de temporada
    season_patterns = [
        re.compile(r"^S(\d+)$", re.IGNORECASE),  # S01, S02
        re.compile(r"^Season[_ ]?(\d+)$", re.IGNORECASE),  # Season 1, Season_1
        re.compile(r"^Temporada[_ ]?(\d+)$", re.IGNORECASE),  # Temporada 1
    ]

    series_path = (
        SERIES_FOLDER
        if os.path.exists(SERIES_FOLDER)
        else os.path.join(MOVIES_FOLDER, "series")
    )

    if not os.path.exists(series_path):
        logger.warning(f"Carpeta de series no existe: {series_path}")
        return series

    def get_season_number(folder_name: str) -> Optional[int]:
        """Extrae el número de temporada del nombre de la carpeta"""
        for pattern in season_patterns:
            match = pattern.match(folder_name)
            if match:
                return int(match.group(1))
        return None

    def clean_title(title: str) -> str:
        """Limpia el título de la serie"""
        return title.replace(".", " ").replace("_", " ").strip()

    def has_valid_episodes(folder_path: str) -> bool:
        """Verifica si la carpeta contiene archivos de video válidos"""
        try:
            for f in os.listdir(folder_path):
                if os.path.isfile(os.path.join(folder_path, f)):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in valid_extensions:
                        return True
        except Exception:
            pass
        return False

    try:
        # Primer nivel: carpetas de series
        for item in os.listdir(series_path):
            item_path = os.path.join(series_path, item)
            if not os.path.isdir(item_path):
                continue

            # Ignorar carpetas especiales
            if item.lower() in [
                "mkv",
                "optimized",
                "processed",
                "thumbnails",
                "pipeline",
                "downloads",
            ]:
                continue

            serie_name = clean_title(item)

            # Si la carpeta parece ser una temporada (contiene S01, Season 1, etc.)
            season_num = get_season_number(item)
            if season_num:
                # El nombre de la serie está en el padre
                parent_path = os.path.dirname(item_path)
                parent_name = os.path.basename(parent_path)
                if parent_name and parent_name.lower() not in [
                    "series",
                    "mkv",
                    "optimized",
                    "processed",
                ]:
                    serie_name = clean_title(parent_name)

            if serie_name not in series:
                series[serie_name] = {
                    "title": serie_name,
                    "path": item_path,
                    "seasons_found": 0,
                    "episodes_found": 0,
                    "has_valid_structure": False,
                }

            # Segundo nivel: carpetas de temporadas
            seasons_count = 0
            episodes_count = 0

            for subitem in os.listdir(item_path):
                subitem_path = os.path.join(item_path, subitem)

                if os.path.isdir(subitem_path):
                    season_num = get_season_number(subitem)
                    if season_num is not None:
                        seasons_count += 1
                        # Contar episodios en esta temporada
                        if has_valid_episodes(subitem_path):
                            try:
                                for f in os.listdir(subitem_path):
                                    if os.path.isfile(os.path.join(subitem_path, f)):
                                        ext = os.path.splitext(f)[1].lower()
                                        if ext in valid_extensions:
                                            episodes_count += 1
                            except Exception:
                                pass

            series[serie_name]["seasons_found"] += seasons_count
            series[serie_name]["episodes_found"] += episodes_count
            series[serie_name]["has_valid_structure"] = (
                seasons_count > 0 and episodes_count > 0
            )

    except Exception as e:
        logger.error(f"Error escaneando series: {e}")

    # Contar episodios totales
    total_episodes = sum(s["episodes_found"] for s in series.values())

    logger.info(
        f"Escaneadas {len(series)} series con {total_episodes} episodios del sistema de archivos"
    )
    return series


def _parse_filename(filename):
    """Parsea nombre de archivo para extraer título y año"""
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


# Blueprint para las rutas de sincronización
sync_bp = Blueprint("catalog_sync", __name__, url_prefix="/api")


@sync_bp.route("/catalog/sync", methods=["POST"])
@require_auth
def sync_catalog():
    """Sincroniza el catálogo con los archivos físicos"""
    try:
        logger.info("Iniciando sincronización del catálogo...")

        movies_on_disk = _scan_movies_from_filesystem()
        series_on_disk = _scan_series_from_filesystem()

        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)

            db_movies = repo.list_local_content(
                content_type="movie", limit=10000, offset=0
            )
            db_series = repo.list_local_content(
                content_type="series", limit=10000, offset=0
            )

            db_movies_by_path = {m.file_path: m for m in db_movies if m.file_path}
            db_series_by_title = {s.title: s for s in db_series if s.title}

            # Contador de episodios totales en disco
            total_episodes_on_disk = sum(
                s["episodes_found"] for s in series_on_disk.values()
            )

            logger.info(
                f"Películas BBDD: {len(db_movies_by_path)}, disco: {len(movies_on_disk)}"
            )
            logger.info(
                f"Series BBDD: {len(db_series_by_title)}, disco: {len(series_on_disk)}"
            )
            logger.info(f"Episodios (calculados): {total_episodes_on_disk}")

            # Eliminar películas que ya no existen
            deleted_movies = 0
            for file_path, movie in db_movies_by_path.items():
                if file_path not in movies_on_disk:
                    try:
                        repo.delete_local_content(movie.id)
                        deleted_movies += 1
                        logger.info(f"Eliminada película: {movie.title}")
                    except Exception as e:
                        logger.error(f"Error eliminando película {movie.title}: {e}")

            # Eliminar series que ya no existen
            deleted_series = 0
            for title, serie in db_series_by_title.items():
                if title not in series_on_disk:
                    try:
                        repo.delete_local_content(serie.id)
                        deleted_series += 1
                        logger.info(f"Eliminada serie: {title}")
                    except Exception as e:
                        logger.error(f"Error eliminando serie {title}: {e}")

            # Añadir nuevas películas
            added_movies = 0
            omdb_service = _get_omdb_service()

            for file_path, movie_data in movies_on_disk.items():
                if file_path in db_movies_by_path:
                    continue

                try:
                    title = movie_data["title"]
                    year = movie_data["year"]

                    search_results = omdb_service.search_movies_cached(title, year=year, limit=10)
                    imdb_id = None

                    # Filtrar por título Y año exacto para evitar insertar películas incorrectas
                    for result in search_results:
                        result_title = result.get("title", "")
                        result_year = result.get("year")
                        # Comparar títulos de forma más flexible (contiene o igual)
                        title_match = title.lower() in result_title.lower() or result_title.lower() in title.lower()
                        year_match = year and result_year and str(year) == str(result_year)
                        
                        if title_match and year_match:
                            imdb_id = result.get("imdb_id") or result.get("imdbID")
                            break

                    # Si no hay coincidencia exacta de título Y año, NO insertar
                    # Esto evita insertar películas incorrectas en la base de datos
                    if not imdb_id:
                        logger.warning(
                            f"No se encontró coincidencia exacta para película: {title} ({year}). "
                            f"Resultados encontrados: {[r.get('title') + ' (' + str(r.get('year')) + ')' for r in search_results]}"
                        )

                    if imdb_id:
                        omdb_data = omdb_service.get_movie_by_imdb_id_raw(imdb_id)
                        if omdb_data:
                            # Usar create_or_update_omdb_entry en lugar de create_local_content
                            # para evitar duplicación entre omdb_entries y local_content
                            repo.create_or_update_omdb_entry(omdb_data)
                            added_movies += 1
                            title = omdb_data.get("Title") or title
                            logger.info(f"Añadida película desde OMDB: {title}")
                    else:
                        # Película sin imdb_id, guardar en local_content como fallback
                        content_data = {
                            "title": title,
                            "year": str(year) if year else None,
                            "type": "movie",
                            "file_path": file_path,
                        }
                        repo.create_local_content(content_data)
                        added_movies += 1
                        logger.info(f"Añadida película sin IMDB: {title}")
                except Exception as e:
                    logger.error(f"Error añadiendo película {title}: {e}")

            # Añadir nuevas series (UNA entrada por serie, NO por episodio)
            added_series = 0

            for serie_name, serie_data in series_on_disk.items():
                if serie_name in db_series_by_title:
                    # La serie ya existe, actualizar total_seasons si ha cambiado
                    serie_record = db_series_by_title[serie_name]
                    if serie_record.total_seasons != serie_data["seasons_found"]:
                        try:
                            repo.update_local_content(
                                serie_record.id,
                                {"total_seasons": serie_data["seasons_found"]},
                            )
                            logger.info(
                                f"Actualizada serie {serie_name}: {serie_data['seasons_found']} temporadas"
                            )
                        except Exception as e:
                            logger.error(f"Error actualizando serie {serie_name}: {e}")
                    continue

                # Buscar en OMDB (UNA SOLA VEZ por serie)
                try:
                    search_results = omdb_service.search_series_cached(
                        serie_name, year=serie_data.get("year"), limit=10
                    )
                    imdb_id = None
                    
                    # Obtener año de la serie si está disponible
                    serie_year = serie_data.get("year")

                    # Filtrar por título Y año exacto para evitar insertar series incorrectas
                    for result in search_results:
                        result_title = result.get("title", "")
                        result_year = result.get("year")
                        # Comparar títulos de forma más flexible (contiene o igual)
                        title_match = serie_name.lower() in result_title.lower() or result_title.lower() in serie_name.lower()
                        year_match = serie_year and result_year and str(serie_year) == str(result_year)
                        
                        if title_match and year_match:
                            imdb_id = result.get("imdb_id") or result.get("imdbID")
                            break

                    # Si no hay coincidencia exacta de título Y año, NO insertar
                    # Esto evita insertar series incorrectas en la base de datos
                    if not imdb_id:
                        logger.warning(
                            f"No se encontró coincidencia exacta para serie: {serie_name} ({serie_year}). "
                            f"Resultados encontrados: {[r.get('title') + ' (' + str(r.get('year')) + ')' for r in search_results]}"
                        )

                    if imdb_id:
                        omdb_data = omdb_service.get_serie_by_imdb_id_raw(imdb_id)
                        if omdb_data:
                            # Descargar póster si hay URL
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
                                except Exception as e:
                                    logger.warning(f"Error descargando póster: {e}")

                            # Usar create_or_update_omdb_entry en lugar de create_local_content
                            # para evitar duplicación entre omdb_entries y local_content
                            repo.create_or_update_omdb_entry(omdb_data, poster_bytes)
                            added_series += 1
                            logger.info(
                                f"Añadida serie desde OMDB: {omdb_data.get('Title')} ({omdb_data.get('totalSeasons')} temporadas)"
                            )
                    else:
                        # Serie sin IMDB, crear con datos básicos en local_content
                        content_data = {
                            "title": serie_name,
                            "type": "series",
                            "total_seasons": serie_data["seasons_found"],
                            "file_path": serie_data["path"],
                        }
                        repo.create_local_content(content_data)
                        added_series += 1
                        logger.info(
                            f"Añadida serie sin IMDB: {serie_name} ({serie_data['seasons_found']} temporadas)"
                        )
                except Exception as e:
                    logger.error(f"Error añadiendo serie {serie_name}: {e}")

        result = {
            "success": True,
            "message": "Sincronización completada",
            "movies_on_disk": len(movies_on_disk),
            "series_on_disk": len(series_on_disk),
            "episodes_on_disk": total_episodes_on_disk,
            "deleted_movies": deleted_movies,
            "deleted_series": deleted_series,
            "added_movies": added_movies,
            "added_series": added_series,
        }

        _invalidate_movie_repository_cache()

        logger.info(f"Sincronización completada: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return jsonify({"error": str(e)}), 500
