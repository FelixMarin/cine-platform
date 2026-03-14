"""
Funciones de sincronización del catálogo con el sistema de archivos
"""
import os
import re
import logging
from flask import Blueprint, jsonify, request
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    get_catalog_repository,
    get_catalog_repository_session,
)
from src.adapters.outgoing.services.omdb.cached_client import get_omdb_service_cached
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# Rutas de archivos
MOVIES_FOLDER = getattr(settings, 'MOVIES_FOLDER', '/mnt/DATA_2TB/audiovisual')
MOVIES_BASE_PATH = getattr(settings, 'MOVIES_BASE_PATH', '/mnt/DATA_2TB/audiovisual/mkv')
SERIES_FOLDER = getattr(settings, 'SERIES_FOLDER', '/mnt/DATA_2TB/audiovisual/series')

_omdb_service = None


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
                    'title': title,
                    'year': year,
                    'file_path': file_path,
                    'category': category,
                    'filename': filename
                }
    except Exception as e:
        logger.error(f"Error escaneando películas: {e}")
    
    logger.info(f"Escaneadas {len(movies)} películas del sistema de archivos")
    return movies


def _scan_series_from_filesystem():
    """Escanea series del sistema de archivos"""
    series = {}
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
    
    series_path = SERIES_FOLDER if os.path.exists(SERIES_FOLDER) else os.path.join(MOVIES_FOLDER, 'series')
    
    if not os.path.exists(series_path):
        logger.warning(f"Carpeta de series no existe: {series_path}")
        return series
    
    try:
        for item in os.listdir(series_path):
            item_path = os.path.join(series_path, item)
            if not os.path.isdir(item_path):
                continue
            
            if item.lower() in ['mkv', 'optimized', 'processed', 'thumbnails', 'pipeline']:
                continue
            
            if re.search(r'\.S\d+', item, re.IGNORECASE):
                serie_name = _parse_season_folder(item)
            else:
                serie_name = item.replace('.', ' ').strip()
            
            if serie_name not in series:
                series[serie_name] = {
                    'title': serie_name,
                    'path': item_path,
                    'files': []
                }
            
            for filename in os.listdir(item_path):
                file_path = os.path.join(item_path, filename)
                if not os.path.isfile(file_path):
                    continue
                
                ext = os.path.splitext(filename)[1].lower()
                if ext not in valid_extensions:
                    continue
                
                series[serie_name]['files'].append({
                    'filename': filename,
                    'file_path': file_path
                })
    except Exception as e:
        logger.error(f"Error escaneando series: {e}")
    
    logger.info(f"Escaneadas {len(series)} series del sistema de archivos")
    return series


def _parse_filename(filename):
    """Parsea nombre de archivo para extraer título y año"""
    name_without_ext = filename.rsplit('.', 1)[0]
    name_clean = name_without_ext
    for suffix in ['-optimized', '-HD', '-4K', '-BluRay', '-WEB', '-DL', '-AC3']:
        name_clean = name_clean.replace(suffix, '')
    
    year = None
    year_match = re.search(r'\((\d{4})\)', name_clean)
    if year_match:
        year = int(year_match.group(1))
        name_clean = re.sub(r'\(\d{4}\)', '', name_clean)
    
    if year is None:
        year_match = re.search(r'[.\-_ ](\d{4})[.\-_ ]', name_clean)
        if year_match:
            year = int(year_match.group(1))
            name_clean = name_clean.replace(year_match.group(0), ' ')
    
    if year is None:
        year_match = re.search(r'(\d{4})$', name_clean.strip())
        if year_match:
            year = int(year_match.group(1))
            name_clean = name_clean[:-4].strip()
    
    title = name_clean.replace('-', ' ').replace('_', ' ').strip()
    title = re.sub(r'\s+', ' ', title)
    
    return title, year


def _parse_season_folder(folder_name):
    """Parsea nombre de carpeta de temporada"""
    season_match = re.search(r'\.S(\d+)', folder_name, re.IGNORECASE)
    if season_match:
        serie_name = folder_name[:season_match.start()]
        return serie_name.replace('.', ' ').strip()
    return folder_name.replace('.', ' ').strip()


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
            
            db_movies = repo.list_local_content(content_type="movie", limit=10000, offset=0)
            db_series = repo.list_local_content(content_type="series", limit=10000, offset=0)
            
            db_movies_by_path = {m.file_path: m for m in db_movies if m.file_path}
            db_series_by_title = {s.title: s for s in db_series if s.title}
            
            logger.info(f"Películas BBDD: {len(db_movies_by_path)}, disco: {len(movies_on_disk)}")
            logger.info(f"Series BBDD: {len(db_series_by_title)}, disco: {len(series_on_disk)}")
            
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
                    title = movie_data['title']
                    year = movie_data['year']
                    
                    search_results = omdb_service.search_movies_cached(title, limit=5)
                    imdb_id = None
                    
                    for result in search_results:
                        result_title = result.get('title', '')
                        result_year = result.get('year')
                        if result_title.lower() == title.lower():
                            if year and result_year and str(year) == str(result_year):
                                imdb_id = result.get('imdb_id') or result.get('imdbID')
                                break
                            elif not year:
                                imdb_id = result.get('imdb_id') or result.get('imdbID')
                                break
                    
                    if not imdb_id and search_results:
                        imdb_id = search_results[0].get('imdb_id') or search_results[0].get('imdbID')
                    
                    if imdb_id:
                        omdb_data = omdb_service.get_movie_by_imdb_id(imdb_id)
                        if omdb_data:
                            content_data = {
                                'imdb_id': imdb_id,
                                'title': omdb_data.get('title') or title,
                                'year': omdb_data.get('year') or (str(year) if year else None),
                                'genre': omdb_data.get('genre'),
                                'plot': omdb_data.get('plot'),
                                'poster_url': omdb_data.get('poster'),
                                'imdb_rating': omdb_data.get('imdb_rating'),
                                'type': 'movie',
                                'file_path': file_path,
                                'runtime': omdb_data.get('runtime'),
                                'director': omdb_data.get('director'),
                                'actors': omdb_data.get('actors'),
                            }
                            repo.create_local_content(content_data)
                            added_movies += 1
                            logger.info(f"Añadida película: {content_data['title']}")
                except Exception as e:
                    logger.error(f"Error añadiendo película {title}: {e}")
            
            # Añadir nuevas series
            added_series = 0
            for serie_name, serie_data in series_on_disk.items():
                if serie_name in db_series_by_title:
                    continue
                
                try:
                    search_results = omdb_service.search_movies_cached(serie_name, limit=5)
                    imdb_id = None
                    
                    for result in search_results:
                        result_title = result.get('title', '')
                        if result_title.lower() == serie_name.lower():
                            imdb_id = result.get('imdb_id') or result.get('imdbID')
                            break
                    
                    if not imdb_id and search_results:
                        imdb_id = search_results[0].get('imdb_id') or search_results[0].get('imdbID')
                    
                    if imdb_id:
                        omdb_data = omdb_service.get_movie_by_imdb_id(imdb_id)
                        if omdb_data:
                            content_data = {
                                'imdb_id': imdb_id,
                                'title': omdb_data.get('title') or serie_name,
                                'year': omdb_data.get('year'),
                                'genre': omdb_data.get('genre'),
                                'plot': omdb_data.get('plot'),
                                'poster_url': omdb_data.get('poster'),
                                'imdb_rating': omdb_data.get('imdb_rating'),
                                'type': 'series',
                                'total_seasons': omdb_data.get('total_seasons'),
                                'file_path': serie_data['path'],
                            }
                            repo.create_local_content(content_data)
                            added_series += 1
                            logger.info(f"Añadida serie: {content_data['title']}")
                except Exception as e:
                    logger.error(f"Error añadiendo serie {serie_name}: {e}")
        
        result = {
            "success": True,
            "message": "Sincronización completada",
            "movies_on_disk": len(movies_on_disk),
            "series_on_disk": len(series_on_disk),
            "deleted_movies": deleted_movies,
            "deleted_series": deleted_series,
            "added_movies": added_movies,
            "added_series": added_series
        }
        
        logger.info(f"Sincronización completada: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return jsonify({"error": str(e)}), 500
