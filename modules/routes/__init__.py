# modules/routes/__init__.py
"""
Módulos de rutas separados por dominio:
- auth: Autenticación (login, logout)
- streaming: Reproducción de video (play, stream)
- thumbnails: Miniaturas
- optimizer: Optimización de video
- api: Endpoints JSON
- admin: Panel de admin
- outputs: Archivos de salida
"""

import os
import queue as queue_module
import logging

logger = logging.getLogger(__name__)

# Importar blueprints
from .auth import auth_bp
from .streaming import streaming_bp
from .thumbnails import thumbnails_bp
from .optimizer import optimizer_bp, processing_queue, processing_status
from .api import api_bp
from .admin import admin_bp
from .outputs import outputs_bp


def register_all_blueprints(app, auth_service, media_service, optimizer_service):
    """
    Registra todos los blueprints en la aplicación Flask
    """
    # Importar worker para iniciar el worker
    from modules.worker import start_worker
    
    # Crear colas y estados para el worker
    worker_queue = queue_module.Queue()
    worker_status = {
        "current": None,
        "queue_size": 0,
        "log_line": "",
        "frames": 0,
        "fps": 0,
        "time": "",
        "speed": "",
        "video_info": {},
        "cancelled": False,
        "last_update": 0
    }
    
    # Iniciar worker
    start_worker(worker_queue, worker_status, optimizer_service)
    
    # Asignar servicios a cada blueprint
    # Usar las funciones de inicialización para actualizar variables globales
    from .auth import init_auth_service
    init_auth_service(auth_service)
    
    from .streaming import init_media_service as init_streaming_media
    init_streaming_media(media_service)
    
    from .thumbnails import init_media_service as init_thumbnails_media
    init_thumbnails_media(media_service)
    
    from .api import init_media_service as init_api_media
    init_api_media(media_service)
    
    # El optimizer tiene su propia inicialización
    optimizer_bp.init_services(optimizer_service, media_service, worker_queue, worker_status)
    
    outputs_bp.init_services(optimizer_service, media_service)
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(streaming_bp)
    app.register_blueprint(thumbnails_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(outputs_bp)
    
    # Registrar after_request para headers de seguridad
    @app.after_request
    def add_security_headers(response):
        """Añadir headers de seguridad a todas las respuestas"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if response.content_type == 'application/json':
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        
        return response
    
    logger.info("✅ Todos los blueprints registrados correctamente")


def create_blueprints(auth_service, media_service, optimizer_service):
    """
    Función legacy para compatibilidad con código existente.
    Crea un blueprint que contiene todos los blueprints.
    """
    from flask import Flask
    
    # Crear una app temporal para registrar todo
    # El llamador debe usar register_all_blueprints directamente
    return None
