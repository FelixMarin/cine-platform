"""
Rutas de Descarga - Endpoints para búsqueda y descarga de torrents

Proporciona endpoints para:
- Buscar películas en Prowlarr y Jackett (en paralelo)
- Iniciar descargas de torrents
- Consultar estado de descargas
- Gestionar optimizaciones con GPU
"""

import logging
import os
import asyncio
import uuid
import requests
from flask import (
    Blueprint,
    jsonify,
    request,
    render_template,
    session,
    redirect,
    url_for,
)
from src.infrastructure.config.settings import settings
from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role

logger = logging.getLogger(__name__)

# Blueprint para las rutas de descarga API
download_api_bp = Blueprint("download", __name__, url_prefix="/api")

# Blueprint para la página de búsqueda (HTML)
search_page_bp = Blueprint("search_page", __name__, url_prefix="")

# Instancias de clientes (se inicializan en init_download_routes)
_prowlarr_client = None
_transmission_client = None
_jackett_client = None

# Instancia del optimizador
_torrent_optimizer = None


def init_download_routes(
    prowlarr_client=None,
    transmission_client=None,
    jackett_client=None,
    torrent_optimizer=None,
):
    """
    Inicializa las rutas de descarga con los clientes necesarios

    Args:
        prowlarr_client: Instancia de ProwlarrClient
        transmission_client: Instancia de TransmissionClient
        jackett_client: Instancia de JackettClient (opcional)
        torrent_optimizer: Instancia de TorrentOptimizer
    """
    global _prowlarr_client, _transmission_client, _jackett_client, _torrent_optimizer

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

        if settings.JACKETT_API_KEY:
            _jackett_client = JackettClient()
            logger.info("[Download Routes] Jackett inicializado")
        else:
            _jackett_client = None
            logger.info("[Download Routes] Jackett no configurado (sin API key)")

    # Inicializar optimizador
    if torrent_optimizer:
        _torrent_optimizer = torrent_optimizer
    else:
        from src.adapters.outgoing.services.ffmpeg.torrent_optimizer import (
            TorrentOptimizer,
        )

        _torrent_optimizer = TorrentOptimizer(
            upload_folder=settings.UPLOAD_FOLDER,
            output_folder=settings.MOVIES_BASE_PATH,
            transmission_client=_transmission_client,
        )
        logger.info("[Download Routes] TorrentOptimizer inicializado")

    logger.info("[Download Routes] Rutas inicializadas")


# ============================================================================
# ENDPOINT: Buscar películas en Prowlarr y Jackett (búsqueda paralela)
# ============================================================================


@download_api_bp.route("/search-movie", methods=["POST"])
@require_role("admin")
def search_movie():
    """
    Busca películas en Prowlarr y Jackett de forma paralela
    """
    data = request.get_json() or {}
    query = data.get("q") or data.get("query", "").strip()
    limit = data.get("limit", 20)

    if not query:
        return jsonify(
            {"success": False, "error": 'Parámetro de búsqueda "q" es requerido'}
        ), 400

    logger.info(f"[API] Buscando película: '{query}' (límite: {limit} por indexador)")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        results, source_info = loop.run_until_complete(_parallel_search(query, limit))

        results = sorted(
            results,
            key=lambda x: (
                x.get("seeders", 0) if isinstance(x.get("seeders"), int) else 0
            ),
            reverse=True,
        )

        return jsonify(
            {
                "success": True,
                "results": results,
                "query": query,
                "sources": source_info,
                "count": len(results),
            }
        )

    except Exception as e:
        logger.error(f"[API] Error en búsqueda paralela: {str(e)}")
        return jsonify({"success": False, "error": f"Error al buscar: {str(e)}"}), 500


async def _parallel_search(query: str, limit: int) -> tuple:
    """Realiza búsqueda en paralelo en Prowlarr y Jackett"""
    logger.info(f"[Parallel Search] 🚀 Iniciando búsqueda paralela para: '{query}'")
    all_results = []
    source_info = {}

    prowlarr_task = None
    jackett_task = None

    if _prowlarr_client:
        prowlarr_task = asyncio.create_task(_search_prowlarr_safe(query, limit))

    if _jackett_client:
        jackett_task = asyncio.create_task(_search_jackett_safe(query, limit))

    if prowlarr_task:
        prowlarr_results, prowlarr_success = await prowlarr_task
        all_results.extend(prowlarr_results)
        source_info["prowlarr"] = {
            "results": len(prowlarr_results),
            "success": prowlarr_success,
        }

    if jackett_task:
        jackett_results, jackett_success = await jackett_task
        all_results.extend(jackett_results)
        source_info["jackett"] = {
            "results": len(jackett_results),
            "success": jackett_success,
        }

    if not source_info:
        logger.warning("[Parallel Search] ⚠️ No hay indexadores disponibles")
        source_info["error"] = "No hay indexadores configurados"

    logger.info(
        f"[Parallel Search] ✅ Búsqueda completada: {len(all_results)} resultados"
    )
    return all_results, source_info


async def _search_prowlarr_safe(query: str, limit: int) -> tuple:
    """Busca en Prowlarr de forma segura"""
    logger.info("[Prowlarr] ▶️ Iniciando búsqueda...")
    try:
        results = _prowlarr_client.search_movies(query, limit=limit)
        formatted = _prowlarr_client.format_results_for_frontend(results)
        for r in formatted:
            r["source"] = "prowlarr"
        logger.info(f"[Prowlarr] ✅ {len(formatted)} resultados")
        return formatted, True
    except Exception as e:
        logger.error(f"[Prowlarr] ❌ Error: {str(e)}")
        return [], False


async def _search_jackett_safe(query: str, limit: int) -> tuple:
    """Busca en Jackett de forma segura"""
    logger.info("[Jackett] ▶️ Iniciando búsqueda...")
    try:
        results = await _jackett_client.search_movies(query, limit=limit)
        formatted = _jackett_client.format_results_for_frontend(results)
        for r in formatted:
            r["source"] = "jackett"
        logger.info(f"[Jackett] ✅ {len(formatted)} resultados")
        return formatted, True
    except Exception as e:
        logger.error(f"[Jackett] ❌ Error: {str(e)}")
        return [], False


# ============================================================================
# ENDPOINT: Iniciar descarga de torrent
# ============================================================================


@download_api_bp.route("/download-torrent", methods=["POST"])
@require_role("admin")
def download_torrent():
    """Inicia una descarga de torrent"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Cuerpo de la petición vacío"}), 400

    url = data.get("url", "").strip()
    result_id = data.get("result_id", "")
    category = data.get("category", "")

    if not url:
        return jsonify({"success": False, "error": "URL del torrent es requerida"}), 400

    if not (url.startswith("magnet:") or url.startswith("http")):
        return jsonify(
            {"success": False, "error": "URL debe ser magnet: o http(s)://"}
        ), 400

    logger.info(f"[API] Iniciando descarga: {url[:50]}...")

    try:
        if category:
            download_dir = os.path.join(settings.MOVIES_BASE_PATH, category)
        else:
            download_dir = os.path.abspath(settings.UPLOAD_FOLDER)

        result = _transmission_client.add_torrent(
            source=url,
            category=category if category else None,
            download_dir=download_dir,
        )

        download_id = str(uuid.uuid4())

        return jsonify(
            {
                "success": True,
                "download": {
                    "id": download_id,
                    "torrent_id": result.get("id"),
                    "name": result.get("name"),
                    "category": category,
                    "status": "downloading",
                    "download_dir": result.get("download_dir"),
                    "hash": result.get("hash"),
                },
                "message": "Descarga iniciada correctamente",
            }
        )

    except Exception as e:
        logger.error(f"[API] Error al iniciar descarga: {str(e)}")
        return jsonify(
            {"success": False, "error": f"Error al iniciar descarga: {str(e)}"}
        ), 500


# ============================================================================
# ENDPOINT: Estado de descargas activas
# ============================================================================


@download_api_bp.route("/download-status", methods=["GET"])
@require_role("admin")
def download_status():
    """Obtiene el estado de las descargas activas"""
    status_filter = request.args.get("status", "all")
    category_filter = request.args.get("category", "")

    logger.info(f"[API] Obteniendo estado de descargas: {status_filter}")

    try:
        logger.info("[API] 📡 Consultando Transmission...")
        torrents = _transmission_client.get_torrents()
        logger.info(f"[API] ✅ Transmission respondió: {len(torrents)} torrents")

        torrents_data = [t.to_dict() for t in torrents]

        if status_filter == "active":
            torrents_data = [t for t in torrents_data if t.get("status") in [4, 6]]
        elif status_filter == "completed":
            torrents_data = [
                t for t in torrents_data if t.get("status") in [0, 1, 2, 3, 5]
            ]

        if category_filter:
            torrents_data = [
                t for t in torrents_data if t.get("category") == category_filter
            ]

        downloads = []
        for t in torrents_data:
            logger.info(
                f"[API] Torrent {t.get('id')}: {t.get('name')[:30]}... - Progress: {t.get('progress')}%"
            )

            download_speed = t.get("rate_download", 0)
            upload_speed = t.get("rate_upload", 0)
            download_speed_formatted = t.get("download_speed_formatted", "0 B/s")
            upload_speed_formatted = t.get("upload_speed_formatted", "0 B/s")
            status_display = t.get("status_display", "unknown")

            size_downloaded = t.get("size_downloaded", 0)
            size_total = t.get("size_total", 0)
            progress = t.get("progress", 0)

            if size_total > 0:
                calculated_progress = (size_downloaded / size_total) * 100
                calculated_progress = min(calculated_progress, 100)
                if abs(calculated_progress - progress) > 1:
                    logger.info(
                        f"[API] Progreso: {progress}% → {calculated_progress:.1f}% ({size_downloaded}/{size_total})"
                    )
                progress = calculated_progress

            eta = t.get("eta", -1)
            eta_formatted = t.get("eta_formatted", "∞")

            download = {
                "id": t.get("id"),
                "title": t.get("name"),
                "hash": t.get("hash", "")[:16] if t.get("hash") else "",
                "status": t.get("status"),
                "status_display": status_display,
                "progress": round(progress, 1),
                "size_total": size_total,
                "size_downloaded": size_downloaded,
                "size_formatted": t.get("size_formatted", "0 B"),
                "download_speed": download_speed,
                "download_speed_formatted": download_speed_formatted,
                "upload_speed": upload_speed,
                "upload_speed_formatted": upload_speed_formatted,
                "eta": eta,
                "eta_formatted": eta_formatted,
                "category": t.get("category", "Peliculas") or "Peliculas",
                "statusDisplay": status_display,
                "sizeTotal": size_total,
                "sizeDownloaded": size_downloaded,
                "sizeFormatted": t.get("size_formatted", "0 B"),
                "downloadSpeed": download_speed,
                "downloadSpeedFormatted": download_speed_formatted,
                "uploadSpeed": upload_speed,
                "uploadSpeedFormatted": upload_speed_formatted,
                "etaFormatted": eta_formatted,
            }
            downloads.append(download)

        active_count = len([t for t in torrents_data if t.get("status") in [4, 6]])

        response = jsonify(
            {
                "success": True,
                "downloads": downloads,
                "stats": {
                    "active_count": active_count,
                    "total_count": len(torrents_data),
                },
            }
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        logger.error(f"[API] Error al obtener estado: {str(e)}")
        return jsonify({"success": False, "error": str(e), "downloads": []}), 500


@download_api_bp.route("/downloads/active", methods=["GET"])
@require_role("admin")
def downloads_active():
    """Alias de download-status para compatibilidad"""
    return download_status()


@download_api_bp.route("/downloads/<int:torrent_id>/cancel", methods=["POST"])
@require_role("admin")
def download_cancel(torrent_id):
    """Cancela una descarga"""
    logger.info(f"[API] Cancelando torrent {torrent_id}")

    try:
        _transmission_client.remove_torrent(torrent_id, delete_files=True)
        return jsonify({"success": True, "message": f"Torrent {torrent_id} cancelado"})
    except Exception as e:
        logger.error(f"[API] Error al cancelar: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/download-url", methods=["POST"])
@require_role("admin")
def download_from_url():
    """Descarga desde URL directa"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Cuerpo vacío"}), 400

    url = data.get("url")
    category = data.get("category", "Peliculas")

    if not url:
        return jsonify({"success": False, "error": "URL requerida"}), 400

    logger.info(f"[API] Descargando desde URL: {url[:50]}...")

    try:
        result = _transmission_client.add_torrent(url, category=category)
        return jsonify(
            {
                "success": True,
                "id": result.get("id"),
                "title": result.get("name"),
                "message": "Descarga iniciada",
            }
        )
    except Exception as e:
        logger.error(f"[API] Error al descargar: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/downloads/<int:torrent_id>/status", methods=["GET"])
@require_role("admin")
def download_status_by_id(torrent_id):
    """Estado de una descarga específica"""
    logger.info(f"[API] Obteniendo estado del torrent {torrent_id}")

    try:
        torrent = _transmission_client.get_torrent(torrent_id)
        if not torrent:
            return jsonify({"success": False, "error": "Torrent no encontrado"}), 404
        return jsonify({"success": True, "download": torrent.to_dict()})
    except Exception as e:
        logger.error(f"[API] Error al obtener estado: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/download-stop/<int:torrent_id>", methods=["POST"])
@require_role("admin")
def download_stop(torrent_id):
    """Detiene una descarga"""
    logger.info(f"[API] Deteniendo torrent {torrent_id}")

    try:
        _transmission_client.stop_torrent(torrent_id)
        return jsonify({"success": True, "message": f"Torrent {torrent_id} detenido"})
    except Exception as e:
        logger.error(f"[API] Error al detener: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/download-start/<int:torrent_id>", methods=["POST"])
@require_role("admin")
def download_start(torrent_id):
    """Reanuda una descarga"""
    logger.info(f"[API] Reanudando torrent {torrent_id}")

    try:
        _transmission_client.start_torrent(torrent_id)
        return jsonify({"success": True, "message": f"Torrent {torrent_id} iniciado"})
    except Exception as e:
        logger.error(f"[API] Error al iniciar: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/download-remove/<int:torrent_id>", methods=["POST"])
@require_role("admin")
def download_remove(torrent_id):
    """Elimina una descarga"""
    data = request.get_json() or {}
    delete_files = data.get("delete_files", False)

    logger.info(f"[API] Eliminando torrent {torrent_id} (delete_files={delete_files})")

    try:
        _transmission_client.remove_torrent(torrent_id, delete_files=delete_files)
        return jsonify({"success": True, "message": f"Torrent {torrent_id} eliminado"})
    except Exception as e:
        logger.error(f"[API] Error al eliminar: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ENDPOINT: Estado de optimizaciones
# ============================================================================


@download_api_bp.route("/optimize-status", methods=["GET"])
@require_role("admin")
def optimize_status():
    """
    Obtiene el estado de las optimizaciones activas
    """
    logger.info("[API] Obteniendo estado de optimizaciones")

    if not _torrent_optimizer:
        return jsonify({"success": False, "error": "Optimizador no disponible"}), 500

    try:
        active = _torrent_optimizer.list_active()
        optimizations = []

        for opt in active:
            optimizations.append(
                {
                    "id": opt.process_id,
                    "title": os.path.basename(opt.input_file),
                    "status": opt.status,
                    "progress": opt.progress,
                    "start_time": opt.start_time,
                }
            )

        return jsonify(
            {
                "success": True,
                "optimizations": optimizations,
                "count": len(optimizations),
                "message": f"{len(optimizations)} optimizaciones activas",
            }
        )
    except Exception as e:
        logger.error(f"[API] Error obteniendo optimizaciones: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ENDPOINT: Obtener categorías disponibles
# ============================================================================


@download_api_bp.route("/download/categories", methods=["GET"])
@require_auth
def get_categories():
    """Obtiene las categorías disponibles"""
    import os

    base_path = settings.MOVIES_BASE_PATH

    if not os.path.exists(base_path):
        logger.error(f"[API] MOVIES_BASE_PATH no existe: {base_path}")
        return jsonify(
            {"success": False, "error": f"La ruta base no existe: {base_path}"}
        ), 500

    try:
        categories = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                categories.append(item)

        categories.sort()
        logger.info(f"[API] Categorías encontradas: {categories}")

        return jsonify({"success": True, "categories": categories})
    except PermissionError:
        logger.error(f"[API] Sin permisos para leer: {base_path}")
        return jsonify(
            {"success": False, "error": "Sin permisos para leer el directorio"}
        ), 500
    except Exception as e:
        logger.error(f"[API] Error leyendo categorías: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ENDPOINT: Test de conexión
# ============================================================================


@download_api_bp.route("/download-test", methods=["GET"])
@require_role("admin")
def download_test():
    """Prueba la conexión con servicios"""
    results = {"prowlarr": False, "transmission": False, "ffmpeg_worker": False}

    try:
        if _prowlarr_client:
            results["prowlarr"] = _prowlarr_client.test_connection()
    except Exception as e:
        logger.warning(f"[API] Error probando Prowlarr: {e}")

    try:
        if _transmission_client:
            results["transmission"] = _transmission_client.test_connection()
    except Exception as e:
        logger.warning(f"[API] Error probando Transmission: {e}")

    try:
        if _torrent_optimizer:
            results["ffmpeg_worker"] = _torrent_optimizer.check_gpu_available()
    except Exception as e:
        logger.warning(f"[API] Error probando FFmpeg worker: {e}")

    return jsonify(
        {
            "success": results["prowlarr"] and results["transmission"],
            "services": results,
        }
    )


# ============================================================================
# PÁGINAS HTML
# ============================================================================


@search_page_bp.route("/search", methods=["GET"])
@require_role("admin")
def search_page():
    """Página de búsqueda"""
    logger.info("[PAGE] Renderizando página de búsqueda")
    return render_template("search.html")


@search_page_bp.route("/downloads", methods=["GET"])
def downloads_page():
    """Página unificada de descargas y optimizaciones"""
    user_role = session.get("user_role")
    if user_role != "admin":
        logger.warning(
            f"[PAGE] Acceso denegado a /downloads para usuario con rol: {user_role}"
        )
        return redirect(url_for("main_page.index"))

    logger.info("[PAGE] Renderizando página de descargas")
    return render_template("downloads.html")


# ============================================================================
# ENDPOINTS: Optimización de Video (TorrentOptimizer)
# ============================================================================


@download_api_bp.route("/optimize/start", methods=["POST"])
@require_role("admin")
def optimize_start():
    """
    Inicia una optimización de video usando TorrentOptimizer
    """
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Cuerpo vacío"}), 400

    input_path = data.get("input_path")
    category = data.get("category", "general")

    if not input_path:
        return jsonify({"success": False, "error": "input_path requerido"}), 400

    if not _torrent_optimizer:
        return jsonify({"success": False, "error": "Optimizador no disponible"}), 500

    try:
        process_id = _torrent_optimizer.start_optimization(
            input_path=input_path, category=category
        )

        logger.info(f"[API] Optimización iniciada: {process_id}")

        return jsonify(
            {
                "success": True,
                "process_id": process_id,
                "message": "Optimización iniciada",
            }
        )

    except FileNotFoundError as e:
        logger.error(f"[API] Archivo no encontrado: {e}")
        return jsonify({"success": False, "error": str(e)}), 404
    except RuntimeError as e:
        logger.error(f"[API] Error de contenedor: {e}")
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"[API] Error al iniciar optimización: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/optimize/status/<process_id>", methods=["GET"])
@require_role("admin")
def optimize_status_v2(process_id):
    """
    Obtiene el estado de una optimización específica
    """
    if not _torrent_optimizer:
        return jsonify({"success": False, "error": "Optimizador no disponible"}), 500

    try:
        progress = _torrent_optimizer.get_progress(process_id)

        if not progress:
            return jsonify({"success": False, "error": "Proceso no encontrado"}), 404

        return jsonify(
            {
                "success": True,
                "optimization": {
                    "id": progress.process_id,
                    "status": progress.status,
                    "progress": progress.progress,
                    "input_file": os.path.basename(progress.input_file),
                    "output_file": os.path.basename(progress.output_file)
                    if progress.output_file
                    else None,
                    "start_time": progress.start_time,
                    "end_time": progress.end_time,
                    "logs": progress.logs[-1000:]
                    if progress.logs
                    else "",  # Últimos 1000 chars
                },
            }
        )

    except Exception as e:
        logger.error(f"[API] Error obteniendo estado: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/optimize/active", methods=["GET"])
@require_role("admin")
def optimize_active():
    """
    Lista todas las optimizaciones activas
    """
    if not _torrent_optimizer:
        return jsonify({"success": False, "error": "Optimizador no disponible"}), 500

    try:
        active = _torrent_optimizer.list_active()

        return jsonify(
            {
                "success": True,
                "optimizations": [
                    {
                        "id": p.process_id,
                        "input_file": os.path.basename(p.input_file),
                        "progress": p.progress,
                        "start_time": p.start_time,
                    }
                    for p in active
                ],
                "count": len(active),
            }
        )

    except Exception as e:
        logger.error(f"[API] Error listando activas: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@download_api_bp.route("/optimize/gpu-status", methods=["GET"])
@require_role("admin")
def gpu_status():
    """Verifica disponibilidad de GPU vía API ffmpeg"""
    if not _torrent_optimizer:
        return jsonify({"success": False, "error": "Optimizador no disponible"}), 500

    try:
        gpu_available = _torrent_optimizer.check_gpu_available()

        gpu_name = None
        if gpu_available:
            try:
                api_url = os.environ.get("FFMPEG_API_URL", "http://ffmpeg-api:8080")
                response = requests.get(f"{api_url}/gpu-status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    gpu_name = data.get("gpu_name")
            except:
                pass

        return jsonify(
            {
                "success": True,
                "gpu_available": gpu_available,
                "gpu_name": gpu_name,
                "message": "GPU disponible" if gpu_available else "GPU no disponible",
            }
        )
    except Exception as e:
        logger.error(f"[API] Error verificando GPU: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
