"""
Rutas de Optimización de Torrents - Endpoints para optimizar archivos descargados

Este módulo proporciona endpoints para:
- Iniciar optimización de un torrent descargado
- Consultar estado de optimización
- Listar optimizaciones activas

Endpoints:
- POST /api/optimize-torrent: Inicia optimización
- GET /api/optimize-torrent/status/<process_id>: Consulta estado
- GET /api/optimize-torrent/active: Lista optimizaciones activas
"""

import logging
import os
import subprocess
import logging
from flask import redirect, Blueprint, jsonify, request
from src.infrastructure.config.settings import settings
from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role
from src.adapters.outgoing.services.ffmpeg import TorrentOptimizer
from src.adapters.outgoing.services.transmission import TransmissionClient


logger = logging.getLogger(__name__)

# Blueprint para las rutas de optimización de torrents
torrent_optimize_bp = Blueprint("torrent_optimize", __name__, url_prefix="/api")

# Instancias globales
_torrent_optimizer = None
_transmission_client = None

# Constantes de rutas de Transmission
TRANSMISSION_COMPLETE = "/downloads/complete"
TRANSMISSION_INCOMPLETE = "/downloads/incomplete"


def init_torrent_optimize_routes(transmission_client=None, torrent_optimizer=None):
    """
    Inicializa las rutas de optimización de torrents

    Args:
        transmission_client: Instancia de TransmissionClient
        torrent_optimizer: Instancia de TorrentOptimizer
    """
    global _torrent_optimizer, _transmission_client

    if transmission_client:
        _transmission_client = transmission_client
    else:
        _transmission_client = TransmissionClient()

    if torrent_optimizer:
        _torrent_optimizer = torrent_optimizer
    else:
        # Pasamos el cliente de Transmission al optimizador
        _torrent_optimizer = TorrentOptimizer(transmission_client=_transmission_client)

    logger.info("[TorrentOptimize] Rutas inicializadas")


# ============================================================================
# ENDPOINT: Iniciar optimización de torrent
# ============================================================================


@torrent_optimize_bp.route("/optimize-torrent", methods=["POST"])
@require_role("admin")
def optimize_torrent():
    """
    Inicia la optimización de un torrent descargado
    
    """
    data = request.get_json() or {}

    torrent_id = data.get("torrent_id")
    category = data.get("category", "action")
    filename = data.get("filename")
    
    logger.info(f"[API] Datos recibidos: {data}")

    # Validar parámetros
    if not torrent_id:
        return jsonify(
            {"success": False, "error": 'Parámetro "torrent_id" es requerido'}
        ), 400

    if not category:
        return jsonify(
            {"success": False, "error": 'Parámetro "category" es requerido'}
        ), 400

    logger.info(
        f"[API] Iniciando optimización para torrent {torrent_id}, categoría: {category}, archivo: {filename}"
    )

    try:
        # El TorrentOptimizer busca el archivo directamente en las carpetas de Transmission
        # No necesitamos validar con Transmission aquí, el botón GPU Optimize
        # solo aparece cuando el torrent está completado (100%)
        
        # Obtener filename si se proporciona (opcional, para buscar directamente)
        filename = data.get("filename")
        
        # Iniciar optimización directamente
        process_id = _torrent_optimizer.start_optimization(
            torrent_id=torrent_id,
            category=category,
            filename=filename
        )

        return jsonify(
            {
                "success": True,
                "process_id": process_id,
                "message": "Optimización iniciada",
                "category": category,
            }
        )

    except FileNotFoundError as e:
        logger.error(f"[API] Archivo no encontrado: {e}")
        return jsonify(
            {"success": False, "error": f"Archivo no encontrado: {str(e)}"}
        ), 404
    except Exception as e:
        logger.error(f"[API] Error al iniciar optimización: {str(e)}", exc_info=True)
        return jsonify(
            {"success": False, "error": f"Error al iniciar optimización: {str(e)}"}
        ), 500


# ============================================================================
# ENDPOINT: Consultar estado de optimización
# ============================================================================


@torrent_optimize_bp.route("/optimize-torrent/status/<process_id>", methods=["GET"])
@require_role("admin")
def get_optimize_status(process_id):
    """
    Consulta el estado de una optimización

    Args:
        process_id: ID del proceso de optimización

    Returns:
        JSON con estado de la optimización
    """
    try:
        progress = _torrent_optimizer.get_progress(process_id)

        if not progress:
            return jsonify(
                {"success": False, "error": f"Proceso {process_id} no encontrado"}
            ), 404

        # Calcular tiempo restante estimado
        eta = None
        if progress.status == "running" and progress.progress > 0:
            elapsed = time.time() - progress.start_time
            eta = int((elapsed / progress.progress) * (100 - progress.progress))

        return jsonify(
            {
                "success": True,
                "process_id": progress.process_id,
                "torrent_id": getattr(progress, 'torrent_id', None),
                "status": progress.status,
                "progress": round(progress.progress, 1),
                "input_file": os.path.basename(progress.input_file),
                "output_file": os.path.basename(progress.output_file),
                "eta_seconds": eta,
                "error": progress.error_message,
            }
        )

    except Exception as e:
        logger.error(f"[API] Error consultando estado: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ENDPOINT: Listar optimizaciones activas
# ============================================================================
@torrent_optimize_bp.route("/active", methods=["GET"])
def active_redirect():
    """Redirige al endpoint correcto"""
    return redirect("/api/optimize-torrent/active")

@torrent_optimize_bp.route("/optimize-torrent/active", methods=["GET"])
@require_role("admin")
def list_active_optimizations():
    """
    Lista las optimizaciones activas

    Returns:
        JSON con lista de optimizaciones en curso
    """
    try:
        active = _torrent_optimizer.list_active()

        return jsonify(
            {
                "success": True,
                "active_count": len(active),
                "optimizations": [
                    {
                        "process_id": p.process_id,
                        "progress": round(p.progress, 1),
                        "input_file": os.path.basename(p.input_file),
                        "status": p.status,
                        "torrent_id": getattr(p, 'torrent_id', None),
                        "category": getattr(p, 'category', None),
                        "original_filename": getattr(p, 'original_filename', None),
                        "error": p.error_message,
                    }
                    for p in active
                ],
            }
        )

    except Exception as e:
        logger.error(f"[API] Error listando optimizaciones: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ENDPOINT: Verificar disponibilidad de GPU
# ============================================================================


@torrent_optimize_bp.route("/optimize-torrent/gpu-status", methods=["GET"])
@require_role("admin")
def check_gpu_status():
    """
    Verifica disponibilidad de GPU en el contenedor worker FFmpeg (ffmpeg-cuda)
    """
    logger.info("[API] Verificando GPU en contenedor ffmpeg-cuda")

    if not _torrent_optimizer:
        return jsonify({"success": False, "error": "Optimizador no disponible"}), 500

    try:
        # Usar TorrentOptimizer que consulta la API de FFmpeg
        gpu_info = _torrent_optimizer.check_gpu_available()
        
        gpu_available = gpu_info.get("available", False)
        gpu_name = gpu_info.get("gpu_name")
        error = gpu_info.get("error")
        
        if error:
            logger.warning(f"[API] Error verificando GPU: {error}")
            return jsonify({
                "success": False,
                "gpu_available": False,
                "gpu_name": None,
                "error": error
            }), 500
        
        if gpu_available and gpu_name:
            logger.info(f"[API] ✅ GPU detectada: {gpu_name}")
            return jsonify({
                "success": True,
                "gpu_available": True,
                "gpu_name": gpu_name,
                "gpu_info": gpu_name
            })
        else:
            logger.warning("[API] ⚠️ No se detectó GPU NVIDIA")
            return jsonify({
                "success": True,
                "gpu_available": False,
                "gpu_name": None,
                "gpu_info": "No GPU detected"
            })
    except Exception as e:
        logger.error(f"[API] ❌ Error verificando GPU: {str(e)}")
        return jsonify(
            {
                "success": False,
                "gpu_available": False,
                "gpu_name": None,
                "error": str(e),
            }
        ), 500


# Importar time para cálculos de ETA
import time
