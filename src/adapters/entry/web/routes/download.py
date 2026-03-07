"""
Rutas de Descarga - Endpoints para búsqueda y descarga de torrents

Proporciona endpoints para:
- Buscar películas en Prowlarr y Jackett (en paralelo)
- Iniciar descargas de torrents
- Consultar estado de descargas
- Gestionar optimizaciones

Endpoints:
- GET /api/search-movie: Busca películas en Prowlarr y Jackett
- POST /api/download-torrent: Inicia una descarga
- GET /api/download-status: Estado de descargas activas
- GET /api/optimize-status: Estado de optimizaciones activas
"""
import logging
import os
import asyncio
from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for
from src.infrastructure.config.settings import settings
from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role

logger = logging.getLogger(__name__)

# Instancia de la cola de optimización
_optimization_queue = None

# Blueprint para las rutas de descarga API
download_api_bp = Blueprint('download', __name__, url_prefix='/api')

# Blueprint para la página de búsqueda (HTML)
search_page_bp = Blueprint('search_page', __name__, url_prefix='')

# Instancias de clientes (se inicializan en init_download_routes)
_prowlarr_client = None
_transmission_client = None
_jackett_client = None


def init_download_routes(prowlarr_client=None, transmission_client=None, jackett_client=None):
    """
    Inicializa las rutas de descarga con los clientes necesarios
    
    Args:
        prowlarr_client: Instancia de ProwlarrClient
        transmission_client: Instancia de TransmissionClient
        jackett_client: Instancia de JackettClient (opcional)
    """
    global _prowlarr_client, _transmission_client, _jackett_client
    
    if prowlarr_client:
        _prowlarr_client = prowlarr_client
    else:
        from src.adapters.outgoing.services.prowlarr import ProwlarrClient
        _prowlarr_client = ProwlarrClient()
    
    if transmission_client:
        _transmission_client = transmission_client
    else:
        from src.adapters.outgoing.services.transmission import TransmissionClient
        _transmission_client = TransmissionClient()
    
    # Inicializar Jackett si está configurado
    if jackett_client:
        _jackett_client = jackett_client
    else:
        from src.adapters.outgoing.services.jackett import JackettClient
        # Verificar si Jackett tiene API key configurada
        if settings.JACKETT_API_KEY:
            _jackett_client = JackettClient()
            logger.info("[Download Routes] Jackett inicializado")
        else:
            _jackett_client = None
            logger.info("[Download Routes] Jackett no configurado (sin API key)")
    
    logger.info("[Download Routes] Rutas inicializadas")


def _init_optimization_queue():
    """Inicializa la cola de optimización"""
    global _optimization_queue
    if _optimization_queue is None:
        from src.adapters.outgoing.services.optimizer import OptimizationQueue
        _optimization_queue = OptimizationQueue(max_concurrent=2)
        logger.info("[Download Routes] Cola de optimización inicializada")


# ============================================================================
# ENDPOINT: Buscar películas en Prowlarr y Jackett (búsqueda paralela)
# ============================================================================

@download_api_bp.route('/search-movie', methods=['POST'])
@require_role('admin')
def search_movie():
    """
    Busca películas en Prowlarr y Jackett de forma paralela
    
    Query Parameters:
        q (str): Término de búsqueda (requerido)
        limit (int): Número máximo de resultados por indexador (opcional, por defecto 20)
    
    Returns:
        JSON con lista de resultados combinados de ambos indexadores
        
    Example:
        POST /api/search-movie
        {
            "q": "matrix",
            "limit": 10
        }
        
        Response:
        {
            "success": true,
            "results": [
                {
                    "guid": "prowlarr://...",
                    "title": "The Matrix 1999 1080p BluRay",
                    "indexer": "RarBG",
                    "source": "prowlarr",
                    "size": "2.18 GB",
                    "seeders": 100,
                    "leechers": 20,
                    "magnet_url": "magnet:?xt=...",
                    "torrent_url": "https://...",
                    "category": "Películas"
                },
                {
                    "guid": "jackett://...",
                    "title": "The Matrix 1999 1080p BluRay",
                    "indexer": "MejorTorrent",
                    "source": "jackett",
                    "size": "2.18 GB",
                    "seeders": 50,
                    "leechers": 10,
                    "magnet_url": "magnet:?xt=...",
                    "torrent_url": "https://...",
                    "category": "Películas"
                }
            ],
            "query": "matrix",
            "sources": {
                "prowlarr": {"results": 5, "success": true},
                "jackett": {"results": 3, "success": true}
            },
            "count": 8
        }
    """
    data = request.get_json() or {}
    query = data.get('q') or data.get('query', '').strip()
    limit = data.get('limit', 20)
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Parámetro de búsqueda "q" es requerido'
        }), 400
    
    logger.info(f"[API] Buscando película: '{query}' (límite: {limit} por indexador)")
    
    # Obtener el loop de eventos de asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # Ejecutar búsqueda paralela
        results, source_info = loop.run_until_complete(
            _parallel_search(query, limit)
        )
        
        # Ordenar resultados por seeders (mayor a menor)
        results = sorted(results, key=lambda x: x.get('seeders', 0) if isinstance(x.get('seeders'), int) else 0, reverse=True)
        
        return jsonify({
            'success': True,
            'results': results,
            'query': query,
            'sources': source_info,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"[API] Error en búsqueda paralela: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al buscar: {str(e)}'
        }), 500


async def _parallel_search(query: str, limit: int) -> tuple:
    """
    Realiza búsqueda en paralelo en Prowlarr y Jackett
    
    Args:
        query: Término de búsqueda
        limit: Límite de resultados por indexador
        
    Returns:
        Tupla (resultados_combined, info_fuentes)
    """
    logger.info(f"[Parallel Search] 🚀 Iniciando búsqueda paralela para: '{query}'")
    all_results = []
    source_info = {}
    
    # Tareas para búsqueda paralela
    prowlarr_task = None
    jackett_task = None
    
    # Buscar en Prowlarr
    if _prowlarr_client:
        prowlarr_task = asyncio.create_task(
            _search_prowlarr_safe(query, limit)
        )
    
    # Buscar en Jackett
    if _jackett_client:
        jackett_task = asyncio.create_task(
            _search_jackett_safe(query, limit)
        )
    
    # Ejecutar ambas búsquedas en paralelo y esperar resultados
    if prowlarr_task:
        prowlarr_results, prowlarr_success = await prowlarr_task
        all_results.extend(prowlarr_results)
        source_info['prowlarr'] = {
            'results': len(prowlarr_results),
            'success': prowlarr_success
        }
    
    if jackett_task:
        jackett_results, jackett_success = await jackett_task
        all_results.extend(jackett_results)
        source_info['jackett'] = {
            'results': len(jackett_results),
            'success': jackett_success
        }
    
    # Si ningún indexador está disponible
    if not source_info:
        logger.warning("[Parallel Search] ⚠️ No hay indexadores disponibles")
        source_info['error'] = 'No hay indexadores configurados'
    
    logger.info(f"[Parallel Search] ✅ Búsqueda completada: {len(all_results)} resultados de {list(source_info.keys())}")
    
    return all_results, source_info


async def _search_prowlarr_safe(query: str, limit: int) -> tuple:
    """
    Busca en Prowlarr de forma segura (con manejo de errores)
    
    Returns:
        Tupla (resultados, success)
    """
    logger.info("[Prowlarr] ▶️ Iniciando búsqueda en Prowlarr...")
    try:
        results = _prowlarr_client.search_movies(query, limit=limit)
        formatted = _prowlarr_client.format_results_for_frontend(results)
        
        # Añadir source a cada resultado
        for r in formatted:
            r['source'] = 'prowlarr'
        
        logger.info(f"[Prowlarr] ✅ Búsqueda completada: {len(formatted)} resultados")
        return formatted, True
    except Exception as e:
        logger.error(f"[Prowlarr] ❌ Error en búsqueda: {str(e)}")
        return [], False


async def _search_jackett_safe(query: str, limit: int) -> tuple:
    """
    Busca en Jackett de forma segura (con manejo de errores)
    
    Returns:
        Tupla (resultados, success)
    """
    logger.info("[Jackett] ▶️ Iniciando búsqueda en Jackett...")
    try:
        results = await _jackett_client.search_movies(query, limit=limit)
        formatted = _jackett_client.format_results_for_frontend(results)
        
        # Añadir source a cada resultado
        for r in formatted:
            r['source'] = 'jackett'
        
        logger.info(f"[Jackett] ✅ Búsqueda completada: {len(formatted)} resultados")
        return formatted, True
    except RuntimeError as e:
        # Error específico de asyncio (como timeout context manager)
        logger.error(f"[Jackett] ❌ Error de asyncio: {str(e)}")
        return [], False
    except Exception as e:
        logger.error(f"[Jackett] ❌ Error en búsqueda: {str(e)}")
        return [], False


# ============================================================================
# ENDPOINT: Iniciar descarga de torrent
# ============================================================================

@download_api_bp.route('/download-torrent', methods=['POST'])
@require_role('admin')
def download_torrent():
    """
    Inicia una descarga de torrent
    
    Request Body (JSON):
        url (str): URL del torrent (magnet o .torrent) - requerido
        result_id (str): ID del resultado seleccionado (opcional)
        category (str): Categoría (Acción, Drama, etc.) - opcional
    
    Returns:
        JSON con información de la descarga iniciada
        
    Example:
        POST /api/download-torrent
        {
            "url": "magnet:?xt=urn:btih:...",
            "result_id": "prowlarr://123",
            "category": "Acción"
        }
        
        Response:
        {
            "success": true,
            "download": {
                "id": "uuid-unico",
                "torrent_id": 123,
                "name": "The Matrix 1999 1080p BluRay",
                "category": "Acción",
                "status": "downloading",
                "download_dir": "/tmp/cineplatform/uploads"
            }
        }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Cuerpo de la petición vacío'
        }), 400
    
    url = data.get('url', '').strip()
    result_id = data.get('result_id', '')
    category = data.get('category', '')
    
    # Log de depuración
    logger.info(f"[API] Received URL length: {len(url)} chars")
    if url:
        logger.info(f"[API] URL starts with: {url[:50]}...")
        logger.info(f"[API] Full URL for debugging: {url}")
    
    # Validar URL
    if not url:
        return jsonify({
            'success': False,
            'error': 'URL del torrent es requerida'
        }), 400
    
    # Validar que la URL sea válida (magnet o http)
    if not (url.startswith('magnet:') or url.startswith('http')):
        return jsonify({
            'success': False,
            'error': 'URL debe ser magnet: o http(s)://'
        }), 400
    
    # Validar categoría si se proporciona
    if category:
        import os
        valid_categories = []
        base_path = settings.MOVIES_BASE_PATH
        
        if os.path.exists(base_path):
            try:
                valid_categories = [d for d in os.listdir(base_path) 
                                   if os.path.isdir(os.path.join(base_path, d))]
            except PermissionError:
                logger.warning(f"[API] Sin permisos para leer: {base_path}")
        
        if category not in valid_categories:
            return jsonify({
                'success': False,
                'error': f'Categoría inválida: {category}. Categorías válidas: {valid_categories}'
            }), 400
    
    logger.info(f"[API] Iniciando descarga: {url[:50]}...")
    logger.info(f"[API] Categoría: {category}, Result ID: {result_id}")
    
    try:
        # Determinar directorio de descarga
        # Si hay categoría, usar la ruta de la categoría (ruta absoluta)
        if category:
            download_dir = os.path.join(settings.MOVIES_BASE_PATH, category)
        else:
            # Convertir ruta relativa a absoluta
            download_dir = os.path.abspath(settings.UPLOAD_FOLDER)
        
        logger.info(f"[API] Directorio de descarga: {download_dir}")
        
        # Añadir el torrent a Transmission
        result = _transmission_client.add_torrent(
            source=url,
            category=category if category else None,
            download_dir=download_dir
        )
        
        # Generar un ID único para seguimiento
        import uuid
        download_id = str(uuid.uuid4())
        
        return jsonify({
            'success': True,
            'download': {
                'id': download_id,
                'torrent_id': result.get('id'),
                'name': result.get('name'),
                'category': category,
                'status': 'downloading',
                'download_dir': result.get('download_dir'),
                'hash': result.get('hash')
            },
            'message': 'Descarga iniciada correctamente'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al iniciar descarga: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al iniciar descarga: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT: Estado de descargas activas
# ============================================================================

@download_api_bp.route('/download-status', methods=['GET'])
@require_role('admin')
def download_status():
    """
    Obtiene el estado de las descargas activas
    
    Query Parameters:
        status (str): Filtrar por estado (active, completed, all) - opcional
        category (str): Filtrar por categoría - opcional
    
    Returns:
        JSON con lista de descargas
        
    Example:
        GET /api/download-status?status=active
        
        Response:
        {
            "success": true,
            "downloads": [
                {
                    "id": 123,
                    "name": "The Matrix 1999 1080p BluRay",
                    "hash": "ABC123...",
                    "status": 4,
                    "status_display": "downloading",
                    "progress": 45.5,
                    "size_total": 2345678901,
                    "size_downloaded": 1073741824,
                    "size_formatted": "2.18 GB",
                    "rate_download": 5242880,
                    "eta": 3600,
                    "eta_formatted": "1h 0m",
                    "category": "Acción"
                }
            ],
            "stats": {
                "active_count": 1,
                "total_count": 5
            }
        }
    """
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', '')
    
    logger.info(f"[API] Obteniendo estado de descargas: {status_filter}")
    
    try:
        logger.info("[API] 📡 Consultando Transmission...")
        torrents = _transmission_client.get_torrents()
        logger.info(f"[API] ✅ Transmission respondió: {len(torrents)} torrents")
        
        # Convertir objetos TorrentDownload a diccionarios
        torrents_data = [t.to_dict() for t in torrents]
        
        # Filtrar por estado
        if status_filter == 'active':
            torrents_data = [t for t in torrents_data if t.get('status') in [4, 6]]  # Downloading o Checking
        elif status_filter == 'completed':
            torrents_data = [t for t in torrents_data if t.get('status') in [0, 1, 2, 3, 5]]  # Completed states
        
        # Filtrar por categoría
        if category_filter:
            torrents_data = [t for t in torrents_data if t.get('category') == category_filter]
        
        # Formatear respuesta
        downloads = []
        for t in torrents_data:
            # Log de depuración para cada torrent
            logger.info(f"[API] Torrent {t.get('id')}: {t.get('name')[:30]}... - "
                       f"Progress: {t.get('progress')}%, "
                       f"Status: {t.get('status_display')}, "
                       f"Download: {t.get('rate_download')} bytes/s")
            
            # Usar los nuevos campos formateados o los antiguos
            download_speed = t.get('rate_download', 0)
            upload_speed = t.get('rate_upload', 0)
            download_speed_formatted = t.get('download_speed_formatted', '0 B/s')
            upload_speed_formatted = t.get('upload_speed_formatted', '0 B/s')
            status_display = t.get('status_display', 'unknown')
            
            # Calcular progress si es 0 pero tenemos size_downloaded y size_total
            progress = t.get('progress', 0)
            size_downloaded = t.get('size_downloaded', 0)
            size_total = t.get('size_total', 0)
            
            # Si progress es 0 pero tenemos tamaños, calcularlo
            if progress == 0 and size_total > 0:
                progress = (size_downloaded / size_total) * 100
                logger.info(f"[API] Calculado progress: {progress:.1f}% ({size_downloaded}/{size_total})")
            
            # Usar eta_formatted o calcularlo
            eta = t.get('eta', -1)
            eta_formatted = t.get('eta_formatted', '∞')
            
            download = {
                'id': t.get('id'),
                'title': t.get('name'),
                'hash': t.get('hash', '')[:16] if t.get('hash') else '',
                'status': t.get('status'),
                'status_display': status_display,
                # Campos en snake_case
                'progress': round(progress, 1),
                'size_total': size_total,
                'size_downloaded': size_downloaded,
                'size_formatted': t.get('size_formatted', '0 B'),
                'download_speed': download_speed,
                'download_speed_formatted': download_speed_formatted,
                'upload_speed': upload_speed,
                'upload_speed_formatted': upload_speed_formatted,
                'eta': eta,
                'eta_formatted': eta_formatted,
                'category': t.get('category', 'Peliculas') or 'Peliculas',
                # Campos en camelCase (para compatibilidad con JS)
                'statusDisplay': status_display,
                'sizeTotal': size_total,
                'sizeDownloaded': size_downloaded,
                'sizeFormatted': t.get('size_formatted', '0 B'),
                'downloadSpeed': download_speed,
                'downloadSpeedFormatted': download_speed_formatted,
                'uploadSpeed': upload_speed,
                'uploadSpeedFormatted': upload_speed_formatted,
                'etaFormatted': eta_formatted
            }
            downloads.append(download)
        
        # Obtener estadísticas
        active_count = len([t for t in torrents_data if t.get('status') in [4, 6]])
        
        # Añadir headers para evitar caché
        response = jsonify({
            'success': True,
            'downloads': downloads,
            'stats': {
                'active_count': active_count,
                'total_count': len(torrents_data)
            }
        })
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f"[API] Error al obtener estado: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'downloads': []
        }), 500


@download_api_bp.route('/downloads/active', methods=['GET'])
@require_role('admin')
def downloads_active():
    """
    Obtiene las descargas activas (alias de download-status para compatibilidad)
    
    Returns:
        JSON con lista de descargas activas
    """
    return download_status()


@download_api_bp.route('/downloads/<int:torrent_id>/cancel', methods=['POST'])
@require_role('admin')
def download_cancel(torrent_id):
    """
    Cancela una descarga (la elimina)
    
    Args:
        torrent_id (int): ID del torrent en Transmission
    
    Returns:
        JSON con resultado de la operación
    """
    logger.info(f"[API] Cancelando torrent {torrent_id}")
    
    try:
        # Eliminar torrent y archivos
        _transmission_client.remove_torrent(torrent_id, delete_files=True)
        
        return jsonify({
            'success': True,
            'message': f'Torrent {torrent_id} cancelado'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al cancelar: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@download_api_bp.route('/download-url', methods=['POST'])
@require_role('admin')
def download_from_url():
    """
    Descarga un torrent desde una URL directa
    
    Request Body (JSON):
        url (str): URL del torrent (.torrent o magnet)
        category (str): Categoría - opcional
    
    Returns:
        JSON con resultado
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Cuerpo vacío'}), 400
    
    url = data.get('url')
    category = data.get('category', 'Peliculas')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400
    
    logger.info(f"[API] Descargando desde URL: {url[:50]}...")
    
    try:
        result = _transmission_client.add_torrent(url, category=category)
        
        return jsonify({
            'success': True,
            'id': result.get('id'),
            'title': result.get('name'),
            'message': 'Descarga iniciada'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al descargar: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        # Obtener todos los torrents
        all_torrents = _transmission_client.get_torrents()
        
        # Filtrar según el estado
        if status_filter == 'active':
            torrents = [t for t in all_torrents if t.status in [3, 4]]  # queued, downloading
        elif status_filter == 'completed':
            torrents = [t for t in all_torrents if t.progress >= 1.0]
        else:
            torrents = all_torrents
        
        # Filtrar por categoría si se especifica
        if category_filter:
            torrents = [t for t in torrents if t.category == category_filter]
        
        # Convertir a diccionario
        downloads = [t.to_dict() for t in torrents]
        
        # Obtener estadísticas
        stats = _transmission_client.get_session_stats()
        
        return jsonify({
            'success': True,
            'downloads': downloads,
            'stats': {
                'active_count': stats.get('active_count', 0),
                'completed_count': len([t for t in all_torrents if t.progress >= 1.0]),
                'total_count': len(all_torrents)
            },
            'count': len(downloads)
        })
        
    except Exception as e:
        logger.error(f"[API] Error al obtener estado: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al obtener estado: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT: Obtener estado de una descarga específica
# ============================================================================

@download_api_bp.route('/downloads/<int:torrent_id>/status', methods=['GET'])
@require_role('admin')
def download_status_by_id(torrent_id):
    """
    Obtiene el estado de una descarga específica
    
    Args:
        torrent_id (int): ID del torrent en Transmission
    
    Returns:
        JSON con detalles del torrent
    """
    logger.info(f"[API] Obteniendo estado del torrent {torrent_id}")
    
    try:
        torrent = _transmission_client.get_torrent(torrent_id)
        
        if not torrent:
            return jsonify({
                'success': False,
                'error': 'Torrent no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'download': torrent.to_dict()
        })
        
    except Exception as e:
        logger.error(f"[API] Error al obtener estado: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ENDPOINT: Detener descarga
# ============================================================================

@download_api_bp.route('/download-stop/<int:torrent_id>', methods=['POST'])
@require_role('admin')
def download_stop(torrent_id):
    """
    Detiene una descarga activa
    
    Args:
        torrent_id (int): ID del torrent en Transmission
    
    Returns:
        JSON con resultado de la operación
    """
    logger.info(f"[API] Deteniendo torrent {torrent_id}")
    
    try:
        _transmission_client.stop_torrent(torrent_id)
        
        return jsonify({
            'success': True,
            'message': f'Torrent {torrent_id} detenido'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al detener: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ENDPOINT: Reanudar descarga
# ============================================================================

@download_api_bp.route('/download-start/<int:torrent_id>', methods=['POST'])
@require_role('admin')
def download_start(torrent_id):
    """
    Reanuda una descarga
    
    Args:
        torrent_id (int): ID del torrent en Transmission
    
    Returns:
        JSON con resultado de la operación
    """
    logger.info(f"[API] Reanudando torrent {torrent_id}")
    
    try:
        _transmission_client.start_torrent(torrent_id)
        
        return jsonify({
            'success': True,
            'message': f'Torrent {torrent_id} iniciado'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al iniciar: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ENDPOINT: Eliminar descarga
# ============================================================================

@download_api_bp.route('/download-remove/<int:torrent_id>', methods=['POST'])
@require_role('admin')
def download_remove(torrent_id):
    """
    Elimina una descarga
    
    Args:
        torrent_id (int): ID del torrent en Transmission
    
    Request Body (JSON):
        delete_files (bool): Si True, elimina también los archivos descargados
    """
    data = request.get_json() or {}
    delete_files = data.get('delete_files', False)
    
    logger.info(f"[API] Eliminando torrent {torrent_id} (delete_files={delete_files})")
    
    try:
        _transmission_client.remove_torrent(torrent_id, delete_files=delete_files)
        
        return jsonify({
            'success': True,
            'message': f'Torrent {torrent_id} eliminado'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al eliminar: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ENDPOINT: Estado de optimizaciones
# ============================================================================

@download_api_bp.route('/optimize-status', methods=['GET'])
@require_role('admin')
def optimize_status():
    """
    Obtiene el estado de las optimizaciones activas
    
    Returns:
        JSON con lista de optimizaciones en proceso
        
    Example:
        GET /api/optimize-status
        
        Response:
        {
            "success": true,
            "optimizations": [],
            "count": 0,
            "message": "No hay optimizaciones activas"
        }
    
    Note:
        Por ahora retorna una respuesta vacía ya que la optimización
        se maneja a través del CLI de optimización. Esta funcionalidad
        puede expandirse en el futuro para integrar con un sistema de colas.
    """
    logger.info("[API] Obteniendo estado de optimizaciones")
    
    # Por ahora retornamos una lista vacía
    # En el futuro esto se podría integrar con un sistema de colas
    # como Celery o Redis Queue
    
    return jsonify({
        'success': True,
        'optimizations': [],
        'count': 0,
        'message': 'No hay optimizaciones activas. Usa el endpoint de optimización del CLI.'
    })


# ============================================================================
# ENDPOINT: Obtener categorías disponibles
# ============================================================================

@download_api_bp.route('/download/categories', methods=['GET'])
@require_auth
def get_categories():
    """
    Obtiene las categorías disponibles leyendo los subdirectorios de MOVIES_BASE_PATH
    
    Returns:
        JSON con lista de categorías formateadas
    """
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    base_path = settings.MOVIES_BASE_PATH
    
    # Validar que la ruta base existe
    if not os.path.exists(base_path):
        logger.error(f"[API] MOVIES_BASE_PATH no existe: {base_path}")
        return jsonify({
            'success': False,
            'error': f'La ruta base de películas no existe: {base_path}'
        }), 500
    
    if not os.path.isdir(base_path):
        logger.error(f"[API] MOVIES_BASE_PATH no es un directorio: {base_path}")
        return jsonify({
            'success': False,
            'error': f'La ruta base de películas no es un directorio: {base_path}'
        }), 500
    
    try:
        # Leer subdirectorios
        categories = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                categories.append(item)
        
        # Ordenar alfabéticamente
        categories.sort()
        
        logger.info(f"[API] Categorías encontradas: {categories}")
        
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except PermissionError:
        logger.error(f"[API] Sin permisos para leer: {base_path}")
        return jsonify({
            'success': False,
            'error': f'Sin permisos para leer el directorio: {base_path}'
        }), 500
    except Exception as e:
        logger.error(f"[API] Error leyendo categorías: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al leer categorías: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT: Test de conexión
# ============================================================================

@download_api_bp.route('/download-test', methods=['GET'])
@require_role('admin')
def download_test():
    """
    Prueba la conexión con Prowlarr y Transmission
    
    Returns:
        JSON con el estado de ambas conexiones
    """
    results = {
        'prowlarr': False,
        'transmission': False
    }
    
    # Test Prowlarr
    try:
        results['prowlarr'] = _prowlarr_client.test_connection()
    except Exception as e:
        logger.warning(f"[API] Error probando Prowlarr: {e}")
    
    # Test Transmission
    try:
        results['transmission'] = _transmission_client.test_connection()
    except Exception as e:
        logger.warning(f"[API] Error probando Transmission: {e}")
    
    return jsonify({
        'success': results['prowlarr'] and results['transmission'],
        'services': results
    })


# ============================================================================
# PÁGINA: Search (HTML)
# ============================================================================

@search_page_bp.route('/search', methods=['GET'])
@require_role('admin')
def search_page():
    """
    Página de búsqueda y descarga de torrents
    
    Returns:
        Template HTML con la interfaz de búsqueda
    """
    logger.info("[PAGE] Renderizando página de búsqueda")
    return render_template('search.html')


@search_page_bp.route('/downloads', methods=['GET'])
def downloads_page():
    """
    Página unificada de descargas y optimizaciones
    Solo accesible para usuarios con rol admin
    
    Returns:
        Template HTML con la interfaz unificada
    """
    # Verificar que el usuario es admin
    user_role = session.get('user_role')
    if user_role != 'admin':
        logger.warning(f"[PAGE] Acceso denegado a /downloads para usuario con rol: {user_role}")
        return redirect(url_for('main_page.index'))
    
    logger.info("[PAGE] Renderizando página de descargas")
    return render_template('downloads.html')


# ============================================================================
# ENDPOINTS: Optimización de Video
# ============================================================================

@download_api_bp.route('/optimize/start', methods=['POST'])
@require_role('admin')
def optimize_start():
    """
    Inicia una optimización de video
    
    Request Body (JSON):
        input_path (str): Ruta del archivo de entrada
        output_path (str): Ruta del archivo de salida
        category (str): Categoría (Acción, Drama, etc.)
        profile (str): Perfil de encoding (opcional, por defecto: balanced)
    
    Returns:
        JSON con ID del trabajo de optimización
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Cuerpo vacío'}), 400
    
    input_path = data.get('input_path')
    output_path = data.get('output_path')
    category = data.get('category', 'Drama')
    profile = data.get('profile', 'balanced')
    
    if not input_path or not output_path:
        return jsonify({'success': False, 'error': 'input_path y output_path requeridos'}), 400
    
    # Inicializar cola si no está
    _init_optimization_queue()
    
    try:
        job_id = _optimization_queue.add_job(
            input_path=input_path,
            output_path=output_path,
            category=category,
            profile=profile
        )
        
        logger.info(f"[API] Optimización iniciada: {job_id}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Optimización iniciada'
        })
        
    except Exception as e:
        logger.error(f"[API] Error al iniciar optimización: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@download_api_bp.route('/optimize/status', methods=['GET'])
@require_role('admin')
def optimize_status_v2():
    """
    Obtiene el estado de todas las optimizaciones
    
    Query Parameters:
        job_id (str, opcional): ID específico del trabajo
        active_only (bool, opcional): Solo trabajos activos
    
    Returns:
        JSON con lista de trabajos
    """
    job_id = request.args.get('job_id')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    
    _init_optimization_queue()
    
    try:
        if job_id:
            job = _optimization_queue.get_job(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Trabajo no encontrado'}), 404
            
            return jsonify({
                'success': True,
                'optimization': job.to_dict()
            })
        
        if active_only:
            jobs = _optimization_queue.get_active_jobs()
        else:
            jobs = _optimization_queue.get_all_jobs()
        
        return jsonify({
            'success': True,
            'optimizations': [j.to_dict() for j in jobs],
            'count': len(jobs)
        })
        
    except Exception as e:
        logger.error(f"[API] Error al obtener estado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@download_api_bp.route('/optimize/cancel/<job_id>', methods=['POST'])
@require_role('admin')
def optimize_cancel(job_id):
    """
    Cancela una optimización
    
    Args:
        job_id: ID del trabajo
    
    Returns:
        JSON con resultado
    """
    _init_optimization_queue()
    
    try:
        success = _optimization_queue.cancel_job(job_id)
        
        if success:
            return jsonify({'success': True, 'message': f'Optimización {job_id} cancelada'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo cancelar'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@download_api_bp.route('/optimize/profiles', methods=['GET'])
@require_role('admin')
def optimize_profiles():
    """
    Obtiene los perfiles de optimización disponibles
    
    Returns:
        JSON con lista de perfiles
    """
    from src.adapters.outgoing.services.ffmpeg.encoder import FFmpegEncoderService
    
    encoder = FFmpegEncoderService()
    
    profiles = [
        {
            'id': key,
            'description': value.get('description', '')
        }
        for key, value in encoder.PROFILES.items()
    ]
    
    return jsonify({
        'success': True,
        'profiles': profiles
    })
