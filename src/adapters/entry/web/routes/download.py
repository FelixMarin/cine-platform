"""
Rutas de Descarga - Endpoints para búsqueda y descarga de torrents

Proporciona endpoints para:
- Buscar películas en Prowlarr
- Iniciar descargas de torrents
- Consultar estado de descargas
- Gestionar optimizaciones

Endpoints:
- GET /api/search-movie: Busca películas en Prowlarr
- POST /api/download-torrent: Inicia una descarga
- GET /api/download-status: Estado de descargas activas
- GET /api/optimize-status: Estado de optimizaciones activas
"""
import logging
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


def init_download_routes(prowlarr_client=None, transmission_client=None):
    """
    Inicializa las rutas de descarga con los clientes necesarios
    
    Args:
        prowlarr_client: Instancia de ProwlarrClient
        transmission_client: Instancia de TransmissionClient
    """
    global _prowlarr_client, _transmission_client
    
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
    
    logger.info("[Download Routes] Rutas inicializadas")


def _init_optimization_queue():
    """Inicializa la cola de optimización"""
    global _optimization_queue
    if _optimization_queue is None:
        from src.adapters.outgoing.services.optimizer import OptimizationQueue
        _optimization_queue = OptimizationQueue(max_concurrent=2)
        logger.info("[Download Routes] Cola de optimización inicializada")


# ============================================================================
# ENDPOINT: Buscar películas en Prowlarr
# ============================================================================

@download_api_bp.route('/search-movie', methods=['POST'])
@require_role('admin')
def search_movie():
    """
    Busca películas en Prowlarr
    
    Query Parameters:
        q (str): Término de búsqueda (requerido)
        limit (int): Número máximo de resultados (opcional, por defecto 20)
    
    Returns:
        JSON con lista de resultados de búsqueda
        
    Example:
        GET /api/search-movie?q=matrix&limit=10
        
        Response:
        {
            "success": true,
            "results": [
                {
                    "guid": "prowlarr://...",
                    "title": "The Matrix 1999 1080p BluRay",
                    "indexer": "RarBG",
                    "size": 2345678901,
                    "size_formatted": "2.18 GB",
                    "seeders": 100,
                    "leechers": 20,
                    "magnet_url": "magnet:?xt=...",
                    "torrent_url": "https://...",
                    "publish_date": "2023-01-15",
                    "categories": ["Movies", "HD"]
                }
            ],
            "query": "matrix"
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
    
    logger.info(f"[API] Buscando película: '{query}'")
    
    try:
        results = _prowlarr_client.search_movies(query, limit=limit)
        
        # Formatear resultados para el frontend
        formatted_results = _prowlarr_client.format_results_for_frontend(results)
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'query': query,
            'count': len(formatted_results)
        })
        
    except Exception as e:
        logger.error(f"[API] Error en búsqueda: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al buscar: {str(e)}'
        }), 500


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
    
    logger.info(f"[API] Iniciando descarga: {url[:50]}...")
    logger.info(f"[API] Categoría: {category}, Result ID: {result_id}")
    
    try:
        # Añadir el torrent a Transmission
        result = _transmission_client.add_torrent(
            source=url,
            category=category if category else None,
            download_dir=settings.UPLOAD_FOLDER
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
        torrents = _transmission_client.get_torrents()
        
        # Filtrar por estado
        if status_filter == 'active':
            torrents = [t for t in torrents if t.get('status') in [4, 6]]  # Downloading o Checking
        elif status_filter == 'completed':
            torrents = [t for t in torrents if t.get('status') in [0, 1, 2, 3, 5]]  # Completed states
        
        # Filtrar por categoría
        if category_filter:
            torrents = [t for t in torrents if t.get('category') == category_filter]
        
        # Formatear respuesta
        downloads = []
        for t in torrents:
            download = {
                'id': t.get('id'),
                'title': t.get('name'),
                'hash': t.get('hashString', '')[:16],
                'status': t.get('status'),
                'status_display': _transmission_client._get_status_text(t.get('status')),
                'progress': t.get('percentDone', 0) * 100,
                'size_total': t.get('sizeWhenDone', 0),
                'size_downloaded': t.get('sizeWhenDone', 0) - t.get('leftUntilDone', 0),
                'size_formatted': _format_bytes(t.get('sizeWhenDone', 0)),
                'download_speed': t.get('rateDownload', 0),
                'download_speed_formatted': _format_bytes(t.get('rateDownload', 0)) + '/s',
                'upload_speed': t.get('rateUpload', 0),
                'upload_speed_formatted': _format_bytes(t.get('rateUpload', 0)) + '/s',
                'eta': t.get('eta', -1),
                'eta_formatted': _format_eta(t.get('eta', -1)),
                'category': t.get('labels', ['Peliculas'])[0] if t.get('labels') else 'Peliculas'
            }
            downloads.append(download)
        
        # Obtener estadísticas
        all_torrents = _transmission_client.get_torrents()
        active_count = len([t for t in all_torrents if t.get('status') in [4, 6]])
        
        return jsonify({
            'success': True,
            'downloads': downloads,
            'stats': {
                'active_count': active_count,
                'total_count': len(all_torrents)
            }
        })
        
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

@download_api_bp.route('/categories', methods=['GET'])
@require_role('admin')
def get_categories():
    """
    Obtiene las categorías disponibles para descargas
    
    Returns:
        JSON con lista de categorías
    """
    from src.adapters.outgoing.services.transmission.client import VALID_CATEGORIES
    
    return jsonify({
        'success': True,
        'categories': VALID_CATEGORIES
    })


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
        return redirect(url_for('catalog.catalog_page'))
    
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
