"""
Logging - Configuración de logging
"""
import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_folder=None):
    """
    Configura el logging de la aplicación
    
    Args:
        log_folder: Carpeta donde se guardarán los logs
        
    Returns:
        Logger configurado
    """
    if log_folder is None:
        log_folder = os.environ.get('LOG_FOLDER', './logs')

    # Crear carpeta de logs
    os.makedirs(log_folder, exist_ok=True)

    # Configurar el logger raíz para que capture todo
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Configurar el logger de la aplicación
    logger = logging.getLogger('cine-platform')
    logger.setLevel(logging.INFO)

    # Evitar duplicar handlers en el logger raíz
    if root_logger.handlers:
        # El logger raíz ya tiene handlers, solo asegurar nivel
        root_logger.setLevel(logging.INFO)
    else:
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler de archivo
        log_file = os.path.join(log_folder, 'cine-platform.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Handler de consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Asegurar que los loggers hijos propaguen al raíz
    logging.getLogger('src').setLevel(logging.INFO)
    logging.getLogger('src').propagate = True

    logger.info(f"Logging configurado. Carpeta: {log_folder}")

    return logger
