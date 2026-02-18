from flask import Flask, request
import os
from dotenv import load_dotenv
from modules.logging.logging_config import setup_logging

# Adaptador OAuth2
from modules.oauth import OAuth2AuthAdapter

# Media y Optimizer
from modules.media import FileSystemMediaRepository
from modules.adapter import FFmpegOptimizerAdapter

# Rutas
from modules.routes import create_blueprints


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
logger = setup_logging(os.environ["LOG_FOLDER"])


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
    #  INYECCIÓN DE SERVICIOS
    # ============================

    logger.info("=== Inicializando servicios ===")

    # 1. Auth (OAuth2 Server)
    oauth_url = os.environ["OAUTH2_URL"]
    auth_service = OAuth2AuthAdapter(base_url=oauth_url)
    logger.info(f"[SERVICE] AuthService inicializado. URL: {oauth_url}")

    # 2. Media
    movies_folder = os.environ["MOVIES_FOLDER"]
    media_service = FileSystemMediaRepository(movies_folder=movies_folder)
    logger.info(f"[SERVICE] MediaService inicializado. Carpeta: {movies_folder}")

    # 3. Optimizer
    optimizer_service = FFmpegOptimizerAdapter(
        upload_folder=os.environ["UPLOAD_FOLDER"],
        temp_folder=os.environ["TEMP_FOLDER"],
        output_folder=os.environ["OUTPUT_FOLDER"]
    )
    logger.info("[SERVICE] OptimizerService inicializado")

    # ============================
    #  RUTAS
    # ============================

    logger.info("=== Registrando blueprints ===")
    main_bp = create_blueprints(auth_service, media_service, optimizer_service)
    app.register_blueprint(main_bp)
    logger.info("[ROUTER] Blueprint principal registrado")

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
        logger.info(f"=== Iniciando Cine Platform en {host}:{port} sin HTTPS ===")
        app.run(
            host=host,
            port=port,
            debug=debug_mode
        )
