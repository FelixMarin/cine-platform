# Constantes del módulo media

# Extensiones de video soportadas
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.flv', '.wmv'}

# Configuración de thumbnails
THUMBNAIL_DEFAULT_SIZE = 320
THUMBNAIL_DEFAULT_QUALITY = 5
THUMBNAIL_WEBP_QUALITY = 75
THUMBNAIL_WEBP_COMPRESSION = 6
THUMBNAIL_DEFAULT_CAPTURE_TIME = 5
THUMBNAIL_CAPTURE_PERCENT = 0.1
THUMBNAIL_MIN_DURATION_FOR_PERCENT = 60

# Configuración de procesamiento
QUEUE_MAXSIZE = 1000
PROCESSING_TIMEOUT = 30
FFPROBE_TIMEOUT = 5
FFPROBE_TIMEOUT_LONG = 10
MAX_CONSECUTIVE_ERRORS = 5
ERROR_SLEEP_TIME = 5

# Sufijos para limpiar nombres de archivo
FILENAME_SUFFIXES_TO_REMOVE = ["-optimized", "_optimized", "-serie"]
