"""
Cine Platform - Servidor Principal
Arquitectura Hexagonal
"""

import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

from src.adapters.config.dependencies import (
    get_continue_watching_use_case,
    get_estimate_size_use_case,
    get_list_movies_use_case,
    get_list_series_use_case,
    get_login_use_case,
    get_logout_use_case,
    get_optimize_movie_use_case,
    get_search_use_case,
    get_track_progress_use_case,
    init_all,
)

# ============================
#  IMPORTS - ARQUITECTURA HEXAGONAL
# ============================
# Configuración
from src.infrastructure.config.settings import settings

# Logging
from src.infrastructure.logging import setup_logging

print("[ARCH] Usando nueva arquitectura hexagonal (src/)")


# ============================
#  CARGA DE ENTORNO (DEV / PROD)
# ============================

# Detectar entorno
env = os.environ.get("APP_ENV", "production")

if env == "development":
    load_dotenv(".env.dev")
else:
    load_dotenv(".env")

print(f"[ENV] Ejecutando en modo: {env}")


# ============================
#  LOGGING
# ============================
logger = setup_logging(os.environ.get("LOG_FOLDER"))


def create_app():
    logger.info("=== Creando instancia Flask ===")

    # Ruta base del proyecto (directorio que contiene server.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(
            BASE_DIR, "src", "adapters", "entry", "web", "templates"
        ),
        static_folder=os.path.join(
            BASE_DIR, "src", "adapters", "entry", "web", "static"
        ),
        static_url_path="/static",
    )

    # ============================
    #  SECRET KEY
    # ============================
    secret = os.environ["SECRET_KEY"]
    app.secret_key = secret
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024 * 1024  # 50GB
    app.config["UPLOAD_TIMEOUT"] = 7200  # 2 horas
    app.config["MAX_CONTENT_PATH"] = None
    logger.info(f"[CONFIG] SECRET_KEY cargada: {secret[:8]}********")

    # ============================
    #  COOKIES Y SEGURIDAD
    # ============================

    # Configuración base (producción)
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ["MAX_CONTENT_LENGTH"])
    app.config["SESSION_COOKIE_DOMAIN"] = os.environ["SESSION_COOKIE_DOMAIN"]
    app.config["SESSION_COOKIE_HTTPONLY"] = (
        os.environ["SESSION_COOKIE_HTTPONLY"] == "True"
    )
    app.config["SESSION_COOKIE_SAMESITE"] = os.environ["SESSION_COOKIE_SAMESITE"]
    app.config["SESSION_COOKIE_SECURE"] = os.environ["SESSION_COOKIE_SECURE"] == "True"
    app.config["SESSION_COOKIE_PATH"] = os.environ["SESSION_COOKIE_PATH"]

    # Sesión permanente (31 días) - se activa en login
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
    app.config["SESSION_TYPE"] = "filesystem"

    # Ajustes automáticos para desarrollo
    if env == "development":
        logger.info("[CONFIG] Modo desarrollo: ajustando cookies y seguridad")
        app.config["SESSION_COOKIE_DOMAIN"] = None
        app.config["SESSION_COOKIE_SECURE"] = False

    logger.info("[CONFIG] Cookies configuradas:")
    logger.info(f"  DOMAIN={app.config['SESSION_COOKIE_DOMAIN']}")
    logger.info(f"  SAMESITE={app.config['SESSION_COOKIE_SAMESITE']}")
    logger.info(f"  SECURE={app.config['SESSION_COOKIE_SECURE']}")
    logger.info(f"  PATH={app.config['SESSION_COOKIE_PATH']}")

    # ============================
    #  INICIALIZACIÓN - ARQUITECTURA HEXAGONAL
    # ============================

    logger.info("=== Inicializando servicios ===")

    # Inicializar casos de uso
    init_all()

    # Obtener casos de uso
    list_movies_use_case = get_list_movies_use_case()
    list_series_use_case = get_list_series_use_case()
    search_use_case = get_search_use_case()
    track_progress_use_case = get_track_progress_use_case()
    continue_watching_use_case = get_continue_watching_use_case()
    optimize_movie_use_case = get_optimize_movie_use_case()
    estimate_size_use_case = get_estimate_size_use_case()
    login_use_case = get_login_use_case()
    logout_use_case = get_logout_use_case()

    logger.info("[ARCH] Casos de uso inicializados:")
    logger.info(f"  - ListMoviesUseCase: {list_movies_use_case}")
    logger.info(f"  - SearchUseCase: {search_use_case}")
    logger.info(f"  - TrackProgressUseCase: {track_progress_use_case}")
    logger.info(f"  - ContinueWatchingUseCase: {continue_watching_use_case}")
    logger.info(f"  - OptimizeMovieUseCase: {optimize_movie_use_case}")
    logger.info(f"  - EstimateSizeUseCase: {estimate_size_use_case}")
    logger.info(f"  - LoginUseCase: {login_use_case}")
    logger.info(f"  - LogoutUseCase: {logout_use_case}")

    # ============================
    #  REGISTRAR BLUEPRINTS - NUEVAS RUTAS
    # ============================

    logger.info("=== Registrando blueprints ===")

    # Importar blueprints de la nueva arquitectura
    from src.adapters.entry.web.routes import (
        admin_bp,
        admin_page_bp,
        api_bp,
        auth_bp,
        catalog_bp,
        catalog_db_bp,
        comments_bp,
        download_api_bp,
        init_admin_routes,
        init_api_routes,
        init_auth_routes,
        init_catalog_db_routes,
        init_catalog_routes,
        init_download_routes,
        init_optimizer_routes,
        init_outputs_routes,
        init_player_routes,
        init_proxy_routes,
        init_streaming_routes,
        init_thumbnails_routes,
        init_torrent_optimize_routes,
        main_page_bp,
        optimizer_bp,
        optimizer_page_bp,
        outputs_bp,
        player_bp,
        player_page_bp,
        profile_bp,
        proxy_bp,
        search_page_bp,
        series_bp,
        series_page_bp,
        stream_page_bp,
        streaming_bp,
        thumbnails_bp,
        torrent_optimize_bp,
    )

    # Importar blueprint de sincronización del catálogo
    from src.adapters.entry.web.routes.catalog_sync import sync_bp

    # Importar blueprint de historial de optimizaciones
    from src.adapters.entry.web.routes.optimization_history import (
        history_bp,
    )

    # Inicializar rutas
    init_catalog_routes(
        list_movies_use_case=list_movies_use_case,
        list_series_use_case=list_series_use_case,
        search_use_case=search_use_case,
    )
    init_player_routes(
        track_progress_use_case=track_progress_use_case,
        get_continue_watching_use_case=continue_watching_use_case,
    )
    init_auth_routes(login_use_case=login_use_case, logout_use_case=logout_use_case)
    init_optimizer_routes(
        optimize_movie_use_case=optimize_movie_use_case,
        estimate_size_use_case=estimate_size_use_case,
    )
    init_api_routes()
    init_download_routes()
    init_admin_routes()
    init_outputs_routes()
    init_proxy_routes()
    init_streaming_routes()
    init_thumbnails_routes()
    init_catalog_db_routes()

    # Inicializar TorrentOptimizer con parámetros necesarios
    from src.adapters.outgoing.services.ffmpeg import TorrentOptimizer
    from src.adapters.outgoing.services.transmission import TransmissionClient

    _torrent_optimizer = TorrentOptimizer(
        upload_folder=settings.UPLOAD_FOLDER,
        output_folder=settings.MOVIES_BASE_PATH,
    )
    _transmission_client = TransmissionClient()
    init_torrent_optimize_routes(
        transmission_client=_transmission_client, torrent_optimizer=_torrent_optimizer
    )

    # Registrar blueprints
    app.register_blueprint(main_page_bp)  # Página principal y favicon
    app.register_blueprint(series_page_bp)
    app.register_blueprint(series_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(player_bp)
    app.register_blueprint(player_page_bp)  # Página de reproducción
    app.register_blueprint(auth_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(optimizer_page_bp)  # Página del optimizador
    app.register_blueprint(api_bp)
    app.register_blueprint(download_api_bp)
    app.register_blueprint(search_page_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_page_bp)  # Página del admin
    app.register_blueprint(outputs_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(streaming_bp)
    app.register_blueprint(stream_page_bp)  # /stream/ para templates
    app.register_blueprint(thumbnails_bp)
    app.register_blueprint(torrent_optimize_bp)
    app.register_blueprint(catalog_db_bp)
    app.register_blueprint(profile_bp)  # Rutas de perfil de usuario
    app.register_blueprint(history_bp)  # Historial de optimizaciones
    app.register_blueprint(sync_bp)  # Sincronización del catálogo
    app.register_blueprint(comments_bp)  # API de comentarios


    logger.info("[ROUTER] Blueprints registrados correctamente")

    # ============================
    #  CONTEXT PROCESSOR - EXPONER SESIÓN A PLANTILLAS
    # ============================
    @app.context_processor
    def inject_session():
        """Inyecta la sesión en todas las plantillas"""
        from flask import session

        return dict(session=session)

    @app.context_processor
    def utility_processor():
        """Proveedor de utilidades para las plantillas"""
        import hashlib
        import os

        def get_file_version(filepath):
            """Genera un hash del archivo para versionado de assets"""
            full_path = (
                os.path.join(app.static_folder, filepath)
                if app.static_folder
                else filepath
            )
            try:
                with open(full_path, "rb") as f:
                    return hashlib.md5(f.read()).hexdigest()[:8]
            except Exception:
                return (
                    str(int(os.path.getmtime(full_path)))
                    if os.path.exists(full_path)
                    else "1"
                )

        return dict(get_file_version=get_file_version)

    @app.after_request
    def add_no_cache_headers(response):
        """Añadir headers anti-cache para prevenir caching de datos dinámicos"""
        from flask import request

        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    return app


# Crear app global
app = create_app()


# ============================
#  EJECUCIÓN LOCAL
# ============================
if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))

    cert_file = os.environ.get("SSL_CERT_FILE")
    key_file = os.environ.get("SSL_KEY_FILE")

    # SSL solo si existen certificados
    use_ssl = (
        cert_file
        and key_file
        and os.path.exists(cert_file)
        and os.path.exists(key_file)
    )

    debug_mode = env == "development"

    if use_ssl:
        logger.info(f"=== Iniciando Cine Platform en {host}:{port} con HTTPS ===")
        app.run(
            host=host, port=port, debug=debug_mode, ssl_context=(cert_file, key_file)
        )
    else:
        logger.info(f"=== Iniciando Cine Platform en {host}:{port} ===")
        app.run(host=host, port=port, debug=debug_mode)
