"""
Script de compatibilidad - Mantiene módulos antiguos funcionando

Este archivo re-exporta las clases de la nueva estructura hexagonal
para mantener compatibilidad con el código existente en `modules/`
"""
# === RE-EXPORT DESDE CORE ===
from src.core.entities import Movie, Serie, Episode, User, UserRole, Progress, MediaType

# === COMPATIBILIDAD CON adapter.py ===
# El FFmpegOptimizerAdapter usa: IOptimizerService, StateManager, FFmpegHandler, PipelineSteps
# Por ahora, importamos desde los módulos existentes
import modules.adapter
import modules.state
import modules.ffmpeg
import modules.pipeline

# Re-exportar clases antiguas para compatibilidad
FFmpegOptimizerAdapter = modules.adapter.FFmpegOptimizerAdapter
IOptimizerService = modules.core.IOptimizerService
StateManager = modules.state.StateManager
FFmpegHandler = modules.ffmpeg.FFmpegHandler
PipelineSteps = modules.pipeline.PipelineSteps

# === COMPATIBILIDAD CON media.py ===
import modules.media.repository

MediaRepository = modules.media.repository.MediaRepository

# === COMPATIBILIDAD CON omdb_client.py ===
import modules.omdb_client

OMDBClient = modules.omdb_client.OMDBClient

# === COMPATIBILIDAD CON oauth.py ===
import modules.oauth

OAuth2AuthAdapter = modules.oauth.OAuth2AuthAdapter
IAuthService = modules.core.IAuthService

# === COMPATIBILIDAD CON routes ===
import modules.routes.api
import modules.routes.auth
import modules.routes.optimizer
import modules.routes.streaming
import modules.routes.thumbnails

# Re-exportar blueprints
api_bp = modules.routes.api.api_bp
auth_bp = modules.routes.auth.auth_bp
optimizer_bp = modules.routes.optimizer.optimizer_bp
streaming_bp = modules.routes.streaming.streaming_bp
thumbnails_bp = modules.routes.thumbnails.thumbnails_bp

# === COMPATIBILIDAD CON worker.py ===
import modules.worker

worker = modules.worker
start_worker = modules.worker.start_worker
background_worker = modules.worker.background_worker

__all__ = [
    # Core
    'Movie', 'Serie', 'Episode', 'User', 'UserRole', 'Progress', 'MediaType',
    
    # Adapter
    'FFmpegOptimizerAdapter', 'IOptimizerService', 'StateManager',
    'FFmpegHandler', 'PipelineSteps',
    
    # Media
    'MediaRepository',
    
    # OMDB
    'OMDBClient',
    
    # OAuth
    'OAuth2AuthAdapter', 'IAuthService',
    
    # Routes
    'api_bp', 'auth_bp', 'optimizer_bp', 'streaming_bp', 'thumbnails_bp',
    
    # Worker
    'worker', 'start_worker', 'background_worker',
]
