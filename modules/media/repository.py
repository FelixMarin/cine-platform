# Repositorio de medios - Implementación del sistema de archivos

import os
import unicodedata
import threading
import json
import time
from modules.core import IMediaRepository
from modules.media.constants import VIDEO_EXTENSIONS, CACHE_TTL, CACHE_FILE
from modules.media.utils import (
    normalize_path,
    clean_filename,
    is_video_file,
    get_category_from_path,
    sanitize_for_log
)
from modules.media.thumbnail import ThumbnailProcessor
from modules.media import ffmpeg_helper
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))


class FileSystemMediaRepository(IMediaRepository):
    """Repositorio de medios basado en el sistema de archivos"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton para evitar múltiples procesadores"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, movies_folder):
        if hasattr(self, '_initialized'):
            return
            
        self.movies_folder = movies_folder
        logger.info(f"Movies folder: {self.movies_folder}")
        self.thumbnails_folder = os.path.join(movies_folder, "thumbnails")
        logger.info(f"Thumbnails folder: {self.thumbnails_folder}")
        
        # Archivo de caché
        self.cache_file = os.path.join(movies_folder, '.catalog_cache.json')
        self.cache_ttl = 300  # 5 minutos en segundos
        
        # Inicializar el procesador de thumbnails
        self.thumbnail_processor = ThumbnailProcessor(self.thumbnails_folder)
        self.thumbnail_processor.start()
        
        # Exponer atributos del procesador para compatibilidad
        self.thumbnail_queue = self.thumbnail_processor.thumbnail_queue
        self.processed_count = self.thumbnail_processor.processed_count
        self.total_pending = self.thumbnail_processor.total_pending
        self.processing_thread = self.thumbnail_processor.processing_thread
        self.queued_thumbnails = self.thumbnail_processor.queued_thumbnails
        
        self._initialized = True

    def get_movies_folder(self):
        """Devuelve la carpeta base de películas"""
        return self.movies_folder

    def is_path_safe(self, requested_path):
        """
        Verifica que una ruta solicitada está dentro de la carpeta base permitida
        """
        if not requested_path or not isinstance(requested_path, str):
            return False
        
        try:
            # Normalizar rutas
            abs_requested = os.path.abspath(os.path.join(self.movies_folder, requested_path))
            abs_base = os.path.abspath(self.movies_folder)
            
            # Prevenir path traversal con separadores normalizados
            normalized = os.path.normpath(requested_path)
            if '..' in normalized.split(os.sep):
                return False
            
            # Verificar que la ruta solicitada está dentro de la carpeta base
            return os.path.commonpath([abs_requested, abs_base]) == abs_base
        except Exception as e:
            logger.error(f"Error validando ruta: {e}")
            return False

    def _queue_thumbnail_generation(self, video_path, base_name):
        """Añade un thumbnail a la cola de procesamiento"""
        return self.thumbnail_processor.queue_thumbnail(video_path, base_name)

    def _load_cache(self):
        """Carga el catálogo desde caché si es válido"""
        try:
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # Verificar TTL
            if time.time() - cache.get('timestamp', 0) > self.cache_ttl:
                logger.info("🗑️ Caché expirado")
                return None
            
            logger.info(f"📦 Cargando {cache.get('total_videos', 0)} videos desde caché")
            return cache
        except Exception as e:
            logger.error(f"Error cargando caché: {e}")
            return None

    def _save_cache(self, categorias, series, total_videos):
        """Guarda el catálogo en caché"""
        try:
            cache_data = {
                'categorias': categorias,
                'series': series,
                'total_videos': total_videos,
                'timestamp': time.time()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 {total_videos} videos guardados en caché")
        except Exception as e:
            logger.error(f"Error guardando caché: {e}")

    def list_content(self, force_refresh=False):
        """
        Lista todo el contenido con caché para mejorar rendimiento
        
        Args:
            force_refresh: Si es True, ignora la caché y escanea de nuevo
        """
        # Intentar cargar desde caché si no se fuerza refresco
        if not force_refresh:
            cached = self._load_cache()
            if cached:
                return cached['categorias'], cached['series']
        
        # Escaneo completo (tarda 5-10 segundos)
        logger.info("🔍 Escaneando archivos... (puede tardar unos segundos)")
        start_time = time.time()
        
        categorias, series, total_videos = self._scan_files()
        
        scan_time = time.time() - start_time
        logger.info(f"✅ Escaneo completado en {scan_time:.2f} segundos: {total_videos} videos")
        
        # Guardar en caché
        self._save_cache(categorias, series, total_videos)
        
        return categorias, series

    def _scan_files(self):
        """Método privado que realiza el escaneo real del sistema de archivos"""
        categorias = {}
        series = {}
        
        total_videos = 0
        thumbnails_faltantes = 0
        
        # Recopilar thumbnails existentes
        existing_thumbnails = self.thumbnail_processor.get_existing_thumbnails()
        
        for root, _, files in os.walk(self.movies_folder):
            categoria = get_category_from_path(root, self.movies_folder)
            if categoria is None:
                continue

            for file in files:
                try:
                    file = normalize_path(file)
                    
                    if is_video_file(file):
                        total_videos += 1
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, self.movies_folder).replace("\\", "/")
                        
                        base_name = os.path.splitext(file)[0]
                        base_name = unicodedata.normalize('NFC', base_name)
                        clean_name = clean_filename(file)
                        
                        # Verificar si thumbnail existe
                        has_thumbnail = base_name in existing_thumbnails
                        
                        if not has_thumbnail:
                            thumbnails_faltantes += 1
                            # Encolar para generación (solo una vez)
                            self._queue_thumbnail_generation(full_path, base_name)
                            
                            thumbnail_urls = {
                                "jpg": None,
                                "webp": None
                            }
                            primary_thumbnail = "/static/images/default.jpg"
                        else:
                            webp_path = os.path.join(self.thumbnails_folder, f"{base_name}.webp")
                            thumbnail_urls = {
                                "jpg": f"/thumbnails/{base_name}.jpg",
                                "webp": f"/thumbnails/{base_name}.webp" if os.path.exists(webp_path) else None
                            }
                            primary_thumbnail = thumbnail_urls["webp"] or thumbnail_urls["jpg"]

                        item = {
                            "name": clean_name,
                            "path": relative_path,
                            "thumbnail": primary_thumbnail,
                            "thumbnails": thumbnail_urls,
                            "thumbnail_pending": not has_thumbnail
                        }

                        if "-serie" in file.lower():
                            series_name = clean_name.rsplit(" T", 1)[0] if " T" in clean_name else clean_name
                            if series_name not in series:
                                series[series_name] = []
                            series[series_name].append(item)
                        else:
                            if categoria not in categorias:
                                categorias[categoria] = []
                            categorias[categoria].append(item)
                            
                except Exception as e:
                    logger.error(f"Error procesando archivo: {e}")
                    continue

        # Ordenar
        categorias = {
            cat: sorted(pelis, key=lambda x: x["name"])
            for cat, pelis in sorted(categorias.items())
        }

        series = {
            k: sorted(v, key=lambda x: x["name"])
            for k, v in sorted(series.items())
        }

        return categorias, series, total_videos

    def get_thumbnail_status(self):
        """Devuelve el estado actualizado de la generación de thumbnails"""
        return self.thumbnail_processor.get_status()

    def get_safe_path(self, filename):
        """Valida rutas para prevenir path traversal"""
        if not self.is_path_safe(filename):
            return None
        
        filename = unicodedata.normalize("NFC", filename)
        base_dir = os.path.abspath(self.movies_folder)
        target_path = os.path.abspath(os.path.join(base_dir, filename))
        return target_path
    
    def get_thumbnails_folder(self):
        return self.thumbnails_folder

    # Métodos de compatibilidad para tests (delegados a ffmpeg_helper)
    def _check_ffmpeg_webp_support(self):
        """Verifica si ffmpeg soporta WebP"""
        return ffmpeg_helper.check_ffmpeg_webp_support()

    def _generate_thumbnail(self, video_path, thumbnail_path):
        """Genera un thumbnail en la ruta especificada"""
        return ffmpeg_helper.generate_thumbnail(
            video_path, 
            thumbnail_path, 
            is_path_safe_func=self.is_path_safe
        )

    def _get_video_duration(self, video_path):
        """Obtiene la duración del video en segundos"""
        return ffmpeg_helper.get_video_duration(
            video_path, 
            is_path_safe_func=self.is_path_safe
        )

    def _clean_filename(self, filename):
        """Limpia y formatea nombres de archivo"""
        return clean_filename(filename)