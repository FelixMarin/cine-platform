"""
Rutas web - Adaptadores de entrada
"""
from src.adapters.entry.web.routes.catalog import catalog_bp, init_catalog_routes
from src.adapters.entry.web.routes.player import player_bp, init_player_routes
from src.adapters.entry.web.routes.auth import auth_bp, init_auth_routes
from src.adapters.entry.web.routes.optimizer import optimizer_bp, init_optimizer_routes
from src.adapters.entry.web.routes.api import api_bp, init_api_routes
from src.adapters.entry.web.routes.admin import admin_bp, init_admin_routes
from src.adapters.entry.web.routes.outputs import outputs_bp, init_outputs_routes
from src.adapters.entry.web.routes.proxy import proxy_bp, init_proxy_routes
from src.adapters.entry.web.routes.streaming import streaming_bp, init_streaming_routes
from src.adapters.entry.web.routes.thumbnails import thumbnails_bp, init_thumbnails_routes


def register_all_blueprints(app, auth_service=None, media_service=None, optimizer_service=None):
    """
    Registra todos los blueprints en la aplicación Flask.
    Esta función es utilizada por los tests.
    """
    # Registrar blueprints
    app.register_blueprint(catalog_bp)
    app.register_blueprint(player_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(outputs_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(streaming_bp)
    app.register_blueprint(thumbnails_bp)

__all__ = [
    'catalog_bp', 'init_catalog_routes',
    'player_bp', 'init_player_routes',
    'auth_bp', 'init_auth_routes',
    'optimizer_bp', 'init_optimizer_routes',
    'api_bp', 'init_api_routes',
    'admin_bp', 'init_admin_routes',
    'outputs_bp', 'init_outputs_routes',
    'proxy_bp', 'init_proxy_routes',
    'streaming_bp', 'init_streaming_routes',
    'thumbnails_bp', 'init_thumbnails_routes',
]
