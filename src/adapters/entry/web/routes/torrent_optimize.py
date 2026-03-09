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
from flask import Blueprint, jsonify, request
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

    Request Body (JSON):
        torrent_id (int): ID del torrent en Transmission (requerido)
        category (str): Categoría para organizar (requerido)

    Returns:
        JSON con ID del proceso de optimización

    Example:
        POST /api/optimize-torrent
        {
            "torrent_id": 1,
            "category": "action"
        }

        Response:
        {
            "success": true,
            "process_id": "uuid-unico",
            "message": "Optimización iniciada"
        }
    """
    data = request.get_json() or {}

    torrent_id = data.get("torrent_id")
    category = data.get("category", "action")

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
        f"[API] Iniciando optimización para torrent {torrent_id}, categoría: {category}"
    )

    try:
        # Validar progreso del torrent (debe estar >= 99.9% para optimizar)
        # Lo hace el optimizador internamente, pero verificamos aquí para dar mejor error
        torrent = _transmission_client.get_torrent(torrent_id)

        if not torrent:
            return jsonify(
                {"success": False, "error": f"Torrent {torrent_id} no encontrado"}
            ), 404

        # Verificar progreso del torrent
        if torrent.size_when_done > 0:
            progress_percent = (torrent.downloaded_ever / torrent.size_when_done) * 100
        else:
            progress_percent = 0
        
        logger.info(f"[API] Torrent: {torrent.name}, progress={torrent.progress}%, calculated={progress_percent}%")
        
        if progress_percent < 99.9:
            return jsonify(
                {
                    "success": False,
                    "error": f"El torrent no está listo (progreso: {progress_percent:.1f}%). Debe estar al 99.9% o más.",
                }
            ), 400

        # El optimizador ahora maneja todo: buscar archivo, copiar, llamar a ffmpeg-api
        logger.info(f"[API] Iniciando optimización para torrent {torrent_id}, categoría: {category}")

        # Llamar al optimizador con torrent_id y categoría
        process_id = _torrent_optimizer.start_optimization(
            torrent_id=torrent_id, 
            category=category
        )

        return jsonify(
            {
                "success": True,
                "process_id": process_id,
                "message": "Optimización iniciada",
                "input_file": torrent.name,
                "category": category,
            }
        )

    except Exception as e:
        logger.error(f"[API] Error al iniciar optimización: {str(e)}")
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
