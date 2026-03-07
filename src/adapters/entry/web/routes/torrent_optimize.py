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
from flask import Blueprint, jsonify, request
from src.infrastructure.config.settings import settings
from src.adapters.entry.web.middleware.auth_middleware import require_auth, require_role
from src.adapters.outgoing.services.ffmpeg import TorrentOptimizer
from src.adapters.outgoing.services.transmission import TransmissionClient


logger = logging.getLogger(__name__)

# Blueprint para las rutas de optimización de torrents
torrent_optimize_bp = Blueprint('torrent_optimize', __name__, url_prefix='/api')

# Instancias globales
_torrent_optimizer = None
_transmission_client = None


def init_torrent_optimize_routes(transmission_client=None, torrent_optimizer=None):
    """
    Inicializa las rutas de optimización de torrents
    
    Args:
        transmission_client: Instancia de TransmissionClient
        torrent_optimizer: Instancia de TorrentOptimizer
    """
    global _torrent_optimizer, _transmission_client
    
    if torrent_optimizer:
        _torrent_optimizer = torrent_optimizer
    else:
        _torrent_optimizer = TorrentOptimizer()
    
    if transmission_client:
        _transmission_client = transmission_client
    else:
        _transmission_client = TransmissionClient()
    
    logger.info("[TorrentOptimize] Rutas inicializadas")


# ============================================================================
# ENDPOINT: Iniciar optimización de torrent
# ============================================================================

@torrent_optimize_bp.route('/optimize-torrent', methods=['POST'])
@require_role('admin')
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
    
    torrent_id = data.get('torrent_id')
    category = data.get('category', 'action')
    
    # Validar parámetros
    if not torrent_id:
        return jsonify({
            'success': False,
            'error': 'Parámetro "torrent_id" es requerido'
        }), 400
    
    if not category:
        return jsonify({
            'success': False,
            'error': 'Parámetro "category" es requerido'
        }), 400
    
    logger.info(f"[API] Iniciando optimización para torrent {torrent_id}, categoría: {category}")
    
    try:
        # Obtener información del torrent desde Transmission
        torrent = _transmission_client.get_torrent(torrent_id)
        
        if not torrent:
            return jsonify({
                'success': False,
                'error': f'Torrent {torrent_id} no encontrado'
            }), 404
        
        # Verificar que esté completado
        if torrent.status != 6:  # 6 = seeding/completed
            return jsonify({
                'success': False,
                'error': f'El torrent no está completado (estado: {torrent.status})'
            }), 400
        
        # Obtener ruta del archivo
        download_dir = torrent.download_dir or settings.UPLOAD_FOLDER
        input_path = os.path.join(download_dir, torrent.name)
        
        # Verificar que existe
        if not os.path.exists(input_path):
            return jsonify({
                'success': False,
                'error': f'Archivo no encontrado: {input_path}'
            }), 404
        
        logger.info(f"[API] Archivo a optimizar: {input_path}")
        
        # Iniciar optimización
        process_id = _torrent_optimizer.start_optimization(
            input_path=input_path,
            category=category
        )
        
        return jsonify({
            'success': True,
            'process_id': process_id,
            'message': 'Optimización iniciada',
            'input_file': torrent.name,
            'category': category
        })
        
    except Exception as e:
        logger.error(f"[API] Error al iniciar optimización: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al iniciar optimización: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT: Consultar estado de optimización
# ============================================================================

@torrent_optimize_bp.route('/optimize-torrent/status/<process_id>', methods=['GET'])
@require_role('admin')
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
            return jsonify({
                'success': False,
                'error': f'Proceso {process_id} no encontrado'
            }), 404
        
        # Calcular tiempo restante estimado
        eta = None
        if progress.status == 'running' and progress.progress > 0:
            elapsed = time.time() - progress.start_time
            eta = int((elapsed / progress.progress) * (100 - progress.progress))
        
        return jsonify({
            'success': True,
            'process_id': progress.process_id,
            'status': progress.status,
            'progress': round(progress.progress, 1),
            'input_file': os.path.basename(progress.input_file),
            'output_file': os.path.basename(progress.output_file),
            'eta_seconds': eta,
            'error': progress.error_message
        })
        
    except Exception as e:
        logger.error(f"[API] Error consultando estado: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ENDPOINT: Listar optimizaciones activas
# ============================================================================

@torrent_optimize_bp.route('/optimize-torrent/active', methods=['GET'])
@require_role('admin')
def list_active_optimizations():
    """
    Lista las optimizaciones activas
    
    Returns:
        JSON con lista de optimizaciones en curso
    """
    try:
        active = _torrent_optimizer.list_active()
        
        return jsonify({
            'success': True,
            'active_count': len(active),
            'optimizations': [
                {
                    'process_id': p.process_id,
                    'progress': round(p.progress, 1),
                    'input_file': os.path.basename(p.input_file),
                    'status': p.status
                }
                for p in active
            ]
        })
        
    except Exception as e:
        logger.error(f"[API] Error listando optimizaciones: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ENDPOINT: Verificar disponibilidad de GPU
# ============================================================================

@torrent_optimize_bp.route('/optimize-torrent/gpu-status', methods=['GET'])
@require_role('admin')
def check_gpu_status():
    """
    Verifica si hay GPU NVIDIA disponible
    
    Returns:
        JSON con estado de GPU
    """
    try:
        gpu_available = _torrent_optimizer.check_gpu_available()
        
        return jsonify({
            'success': True,
            'gpu_available': gpu_available
        })
        
    except Exception as e:
        logger.error(f"[API] Error verificando GPU: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Importar time para cálculos de ETA
import time
