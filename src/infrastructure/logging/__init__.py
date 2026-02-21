"""
Logging - Configuración de logging
"""
import os
import logging
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
        log_folder = os.environ.get('LOG_FOLDER', '/tmp/cineplatform/logs')
    
    # Crear carpeta de logs
    os.makedirs(log_folder, exist_ok=True)
    
    # Configurar logging
    logger = logging.getLogger('cine-platform')
    logger.setLevel(logging.INFO)
    
    # Evitar duplicar handlers
    if logger.handlers:
        return logger
    
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
    logger.addHandler(file_handler)
    
    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging configurado. Carpeta: {log_folder}")
    
    return logger
