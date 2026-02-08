# transcriber_app/modules/logging/logging_config.py
import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(name="cine-platform", level=logging.DEBUG) -> logging.Logger:
    """
    Configura el logging global del proyecto.
    - name: nombre del logger (por defecto 'cine-platform').
    - level: nivel mínimo de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    Devuelve un logger listo para usar.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Consola
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        # Fichero único cine-platform.log
        fh = logging.FileHandler(LOG_DIR / "cine-platform.log", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # 🔑 Clave: propagar al root para que todos los módulos se vean
    logger.propagate = True
    return logger
