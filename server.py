from flask import Flask
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
    app = Flask(
        __name__,
        template_folder="./templates",
        static_folder="./static",
        static_url_path="/static"
    )

    app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_me")

    # Seguridad
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # --- INYECCIÓN DE DEPENDENCIAS ---

    # 1. Auth (OAuth2Server)
    auth_service = OAuth2AuthAdapter(
	base_url=os.getenv("OAUTH2_URL", "http://oauth2-server.auth.svc.cluster.local:8080")
    )

    # 2. Media
    movies_folder = os.getenv("MOVIES_FOLDER")
    media_service = FileSystemMediaRepository(movies_folder=movies_folder)

    # 3. Optimizer
    optimizer_service = FFmpegOptimizerAdapter(
        upload_folder=os.path.join(os.getcwd(), "uploads"),
        temp_folder=os.path.join(os.getcwd(), "temp"),
        output_folder=os.path.join(os.getcwd(), "outputs")
    )

    # --- RUTAS ---
    main_bp = create_blueprints(auth_service, media_service, optimizer_service)
    app.register_blueprint(main_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))

    logger.info(f"=== Iniciando Cine Platform en {host}:{port} ===")
    app.run(host=host, port=port, debug=False)
