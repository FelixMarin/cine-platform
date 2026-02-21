"""
Adaptador de entrada - Rutas del optimizador
Blueprint para /api/optimizer
"""
import os
from flask import Blueprint, jsonify, request

from src.core.use_cases.optimizer import OptimizeMovieUseCase, EstimateSizeUseCase

logger = None


def setup_logging(log_folder):
    """Setup de logging - se configurará después"""
    import logging
    global logger
    if logger is None:
        logger = logging.getLogger(__name__)
    return logger


optimizer_bp = Blueprint('optimizer', __name__)

# Casos de uso inyectados
_optimize_movie_use_case = None
_estimate_size_use_case = None


def init_optimizer_routes(
    optimize_movie_use_case: OptimizeMovieUseCase = None,
    estimate_size_use_case: EstimateSizeUseCase = None
):
    """Inicializa los casos de uso para las rutas del optimizador"""
    global _optimize_movie_use_case, _estimate_size_use_case
    _optimize_movie_use_case = optimize_movie_use_case
    _estimate_size_use_case = estimate_size_use_case


@optimizer_bp.route('/api/optimizer/optimize', methods=['POST'])
def optimize_video():
    """Añade un video a la cola de optimización"""
    global _optimize_movie_use_case
    
    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        file_path = data.get('file_path')
        profile = data.get('profile', 'balanced')
        
        if not file_path:
            return jsonify({'error': 'file_path es requerido'}), 400
        
        result = _optimize_movie_use_case.execute(file_path, profile)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/optimize-folder', methods=['POST'])
def optimize_folder():
    """Añade todos los videos de una carpeta a la cola"""
    global _optimize_movie_use_case
    
    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        folder_path = data.get('folder_path')
        profile = data.get('profile', 'balanced')
        
        if not folder_path:
            return jsonify({'error': 'folder_path es requerido'}), 400
        
        result = _optimize_movie_use_case.process_folder(folder_path, profile)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/status', methods=['GET'])
def get_status():
    """Obtiene el estado actual del optimizador"""
    global _optimize_movie_use_case
    
    # Si no hay caso de uso, devolver estado simple
    if _optimize_movie_use_case is None:
        return jsonify({
            'status': 'not_initialized',
            'current_video': None,
            'current_step': 0,
            'history': [],
            'message': 'Optimizador no disponible'
        })
    
    try:
        status = _optimize_movie_use_case.get_status()
        
        return jsonify(status)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/cancel', methods=['POST'])
def cancel_current():
    """Cancela el procesamiento actual"""
    global _optimize_movie_use_case
    
    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        success = _optimize_movie_use_case.cancel_current()
        
        return jsonify({'success': success})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/profiles', methods=['GET'])
def get_profiles():
    """Obtiene los perfiles de optimización disponibles"""
    global _optimize_movie_use_case
    
    if _optimize_movie_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        profiles = _optimize_movie_use_case.get_available_profiles()
        
        return jsonify(profiles)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@optimizer_bp.route('/api/optimizer/estimate', methods=['POST'])
def estimate_size():
    """Estima el tamaño de un video optimizado"""
    global _estimate_size_use_case
    
    if _estimate_size_use_case is None:
        return jsonify({'error': 'Servicio no inicializado'}), 500
    
    try:
        data = request.get_json()
        
        file_path = data.get('file_path')
        profile = data.get('profile', 'balanced')
        
        if not file_path:
            return jsonify({'error': 'file_path es requerido'}), 400
        
        estimate = _estimate_size_use_case.execute(file_path, profile)
        
        if estimate:
            return jsonify(estimate)
        else:
            return jsonify({'error': 'No se pudo calcular la estimación'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
