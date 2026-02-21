"""
Cine Platform - Servidor Principal
Arquitectura Hexagonal
"""
from flask import Flask, request
import os
from dotenv import load_dotenv

# ============================
#  IMPORTS - ARQUITECTURA HEXAGONAL
# ============================

# Configuración
from src.infrastructure.config.settings import settings
from src.adapters.config.dependencies import (
    init_all,
    get_list_movies_use_case,
    get_list_series_use_case,
    get_search_use_case,
    get_track_progress_use_case,
    get_continue_watching_use_case,
    get_optimize_movie_use_case,
    get_estimate_size_use_case,
    get_login_use_case,
    get_logout_use_case
)

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

    app = Flask(
        __name__,
        template_folder="./templates",
        static_folder="./static",
        static_url_path="/static"
    )

    # ============================
    #  SECRET KEY
    # ============================
    secret = os.environ["SECRET_KEY"]
    app.secret_key = secret
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    logger.info(f"[CONFIG] SECRET_KEY cargada: {secret[:8]}********")

    # ============================
    #  COOKIES Y SEGURIDAD
    # ============================

    # Configuración base (producción)
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ["MAX_CONTENT_LENGTH"])
    app.config['SESSION_COOKIE_DOMAIN'] = os.environ["SESSION_COOKIE_DOMAIN"]
    app.config['SESSION_COOKIE_HTTPONLY'] = os.environ["SESSION_COOKIE_HTTPONLY"] == "True"
    app.config['SESSION_COOKIE_SAMESITE'] = os.environ["SESSION_COOKIE_SAMESITE"]
    app.config['SESSION_COOKIE_SECURE'] = os.environ["SESSION_COOKIE_SECURE"] == "True"
    app.config['SESSION_COOKIE_PATH'] = os.environ["SESSION_COOKIE_PATH"]
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'

    # Ajustes automáticos para desarrollo
    if env == "development":
        logger.info("[CONFIG] Modo desarrollo: ajustando cookies y seguridad")
        app.config['SESSION_COOKIE_DOMAIN'] = None
        app.config['SESSION_COOKIE_SECURE'] = False

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
        catalog_bp, init_catalog_routes,
        player_bp, init_player_routes,
        auth_bp, init_auth_routes,
        optimizer_bp, init_optimizer_routes,
        api_bp, init_api_routes,
        admin_bp, init_admin_routes,
        outputs_bp, init_outputs_routes,
        proxy_bp, init_proxy_routes,
        streaming_bp, init_streaming_routes,
        thumbnails_bp, init_thumbnails_routes
    )
    
    # Inicializar rutas
    init_catalog_routes(
        list_movies_use_case=list_movies_use_case,
        list_series_use_case=list_series_use_case,
        search_use_case=search_use_case
    )
    init_player_routes(
        track_progress_use_case=track_progress_use_case,
        get_continue_watching_use_case=continue_watching_use_case
    )
    init_auth_routes(login_use_case=login_use_case, logout_use_case=logout_use_case)
    init_optimizer_routes(optimize_movie_use_case=optimize_movie_use_case, estimate_size_use_case=estimate_size_use_case)
    init_api_routes()
    init_admin_routes()
    init_outputs_routes()
    init_proxy_routes()
    init_streaming_routes()
    init_thumbnails_routes()
    
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
    
    logger.info("[ROUTER] Blueprints registrados correctamente")

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
            host=host,
            port=port,
            debug=debug_mode,
            ssl_context=(cert_file, key_file)
        )
    else:
        logger.info(f"=== Iniciando Cine Platform en {host}:{port} ===")
        app.run(host=host, port=port, debug=debug_mode)
