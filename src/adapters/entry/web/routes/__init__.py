"""
Rutas web - Adaptadores de entrada
"""

import logging

logger = logging.getLogger(__name__)

from src.adapters.entry.web.routes.admin import (
    admin_bp,
    admin_page_bp,
    init_admin_routes,
)
from src.adapters.entry.web.routes.api import api_bp, init_api_routes
from src.adapters.entry.web.routes.auth import auth_bp, init_auth_routes, main_page_bp
from src.adapters.entry.web.routes.catalog import catalog_bp, init_catalog_routes
from src.adapters.entry.web.routes.catalog_db import (
    catalog_db_bp,
    init_catalog_db_routes,
)
from src.adapters.entry.web.routes.catalog_movies import catalog_movies_bp
from src.adapters.entry.web.routes.catalog_sync import sync_bp
from src.adapters.entry.web.routes.comments import comments_bp
from src.adapters.entry.web.routes.download import (
    download_api_bp,
    init_download_routes,
    search_page_bp,
)
from src.adapters.entry.web.routes.optimization_history import (
    history_bp,
    init_history_routes,
)
from src.adapters.entry.web.routes.optimizer import (
    init_optimizer_routes,
    optimizer_bp,
    optimizer_page_bp,
)
from src.adapters.entry.web.routes.outputs import (
    download_bp as outputs_download_bp,
)
from src.adapters.entry.web.routes.outputs import (
    init_outputs_routes,
    outputs_bp,
)
from src.adapters.entry.web.routes.player import (
    init_player_routes,
    player_bp,
    player_page_bp,
)
from src.adapters.entry.web.routes.profile import profile_bp
from src.adapters.entry.web.routes.proxy import init_proxy_routes, proxy_bp
from src.adapters.entry.web.routes.series import series_bp, series_page_bp
from src.adapters.entry.web.routes.streaming import (
    init_streaming_routes,
    stream_page_bp,
    streaming_bp,
)
from src.adapters.entry.web.routes.thumbnails import (
    init_thumbnails_routes,
    thumbnails_bp,
)
from src.adapters.entry.web.routes.torrent_optimize import (
    init_torrent_optimize_routes,
    torrent_optimize_bp,
)


def register_all_blueprints(
    app, auth_service=None, media_service=None, optimizer_service=None
):
    """
    Registra todos los blueprints en la aplicación Flask.
    Esta función es utilizada por los tests.
    """
    # Registrar blueprints
    app.register_blueprint(main_page_bp)  # Página principal y favicon
    app.register_blueprint(
        series_page_bp
    )  # Rutas de páginas de series (antes de otros para evitar conflictos)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(catalog_movies_bp)  # Nuevo endpoint /api/movies
    # catalog_series_bp ya no se registra (sus endpoints están en series.py)
    app.register_blueprint(player_bp)
    app.register_blueprint(player_page_bp)  # Página de reproducción
    app.register_blueprint(auth_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(optimizer_page_bp)  # Página HTML del optimizador
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_page_bp)  # Página HTML del admin
    app.register_blueprint(api_bp)
    app.register_blueprint(download_api_bp)  # API de descargas (Prowlarr/Transmission)
    app.register_blueprint(outputs_bp)
    app.register_blueprint(outputs_download_bp)  # /download/ - solo admins
    app.register_blueprint(proxy_bp)
    app.register_blueprint(streaming_bp)
    app.register_blueprint(stream_page_bp)  # /stream/ para templates
    app.register_blueprint(thumbnails_bp)
    app.register_blueprint(
        torrent_optimize_bp
    )  # 🔴 AÑADIDO - Endpoints de optimización de torrents
    app.register_blueprint(profile_bp)  # Rutas de perfil de usuario
    app.register_blueprint(history_bp)  # Historial de optimizaciones
    app.register_blueprint(sync_bp)  # Sincronización del catálogo
    app.register_blueprint(series_bp)  # Rutas de series (API)
    app.register_blueprint(comments_bp)  # API de comentarios

    # Log de todas las rutas registradas
    logger.info("=== Rutas registradas ===")
    for rule in app.url_map.iter_rules():
        if "optimization-history" in str(rule):
            logger.info(f"  RUTA ENCONTRADA: {rule} -> {rule.endpoint}")
    logger.info("===========================")

    print("✅ Todos los blueprints registrados correctamente")


__all__ = [
    "catalog_bp",
    "init_catalog_routes",
    "catalog_db_bp",
    "init_catalog_db_routes",
    "player_bp",
    "player_page_bp",
    "init_player_routes",
    "auth_bp",
    "init_auth_routes",
    "optimizer_bp",
    "optimizer_page_bp",
    "init_optimizer_routes",
    "api_bp",
    "init_api_routes",
    "download_api_bp",
    "search_page_bp",
    "init_download_routes",
    "torrent_optimize_bp",
    "init_torrent_optimize_routes",
    "admin_bp",
    "admin_page_bp",
    "init_admin_routes",
    "outputs_bp",
    "init_outputs_routes",
    "proxy_bp",
    "init_proxy_routes",
    "streaming_bp",
    "stream_page_bp",
    "init_streaming_routes",
    "thumbnails_bp",
    "init_thumbnails_routes",
    "history_bp",
    "init_history_routes",
    "series_bp",
    "series_page_bp",
]
