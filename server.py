from flask import Flask, request
import os
from dotenv import load_dotenv
from modules.logging.logging_config import setup_logging

# Adaptador OAuth2 (nuevo)
from modules.oauth import OAuth2AuthAdapter

# Media y Optimizer
from modules.media import FileSystemMediaRepository
from modules.adapter import FFmpegOptimizerAdapter

# Rutas
from modules.routes import create_blueprints


# --- CONFIGURACIÓN ---
load_dotenv()
logger = setup_logging("cine-platform")


def create_app():
    logger.info("=== Creando instancia Flask ===")

    app = Flask(
        __name__,
        template_folder="./templates",
        static_folder="./static",
        static_url_path="/static"
    )

    # SECRET KEY
    secret = os.getenv("SECRET_KEY", "dev_secret_key_change_me")
    app.secret_key = secret
    logger.info(f"[CONFIG] SECRET_KEY cargada: {secret[:8]}********")

    # Seguridad y cookies
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024
    app.config['SESSION_COOKIE_DOMAIN'] = 'ubuntu.tail921051.ts.net'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_PATH'] = '/'

    logger.info("[CONFIG] Cookies configuradas:")
    logger.info(f"  DOMAIN={app.config['SESSION_COOKIE_DOMAIN']}")
    logger.info(f"  SAMESITE={app.config['SESSION_COOKIE_SAMESITE']}")
    logger.info(f"  SECURE={app.config['SESSION_COOKIE_SECURE']}")
    logger.info(f"  PATH={app.config['SESSION_COOKIE_PATH']}")

    # --- Middleware de trazas ---
    @app.before_request
    def log_request_debug():
        logger.debug(f"[REQUEST] {request.method} {request.path}")
        logger.debug(f"[REQUEST] Cookies recibidas: {request.cookies}")

    # --- INYECCIÓN DE DEPENDENCIAS ---
    logger.info("=== Inicializando servicios ===")

    # 1. Auth (OAuth2Server)
    auth_service = OAuth2AuthAdapter(
        base_url=os.getenv("OAUTH2_URL", "http://oauth2-server.auth.svc.cluster.local:8080")
    )
    logger.info("[SERVICE] AuthService inicializado")

    # 2. Media
    movies_folder = os.getenv("MOVIES_FOLDER")
    media_service = FileSystemMediaRepository(movies_folder=movies_folder)
    logger.info(f"[SERVICE] MediaService inicializado. Carpeta: {movies_folder}")

    # 3. Optimizer
    optimizer_service = FFmpegOptimizerAdapter(
        upload_folder=os.path.join(os.getcwd(), "uploads"),
        temp_folder=os.path.join(os.getcwd(), "temp"),
        output_folder=os.path.join(os.getcwd(), "outputs")
    )
    logger.info("[SERVICE] OptimizerService inicializado")

    # --- RUTAS ---
    logger.info("=== Registrando blueprints ===")
    main_bp = create_blueprints(auth_service, media_service, optimizer_service)
    app.register_blueprint(main_bp)
    logger.info("[ROUTER] Blueprint principal registrado")

    return app


# Crear app global
app = create_app()


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))

    logger.info(f"=== Iniciando Cine Platform en {host}:{port} ===")
    app.run(host=host, port=port, debug=False)
