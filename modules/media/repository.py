# Repositorio de medios - Implementación del sistema de archivos

import os
import unicodedata
import threading
import json
import time
from collections import OrderedDict
from datetime import datetime
from modules.core import IMediaRepository
from modules.media.constants import VIDEO_EXTENSIONS, CACHE_TTL, CACHE_FILE, NEW_THRESHOLD_DAYS, UPLOADS_CACHE_FILE
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
        
        # Archivo de registro de subidas
        self.uploads_file = os.path.join(movies_folder, UPLOADS_CACHE_FILE)
        self.uploads_cache = self._load_uploads_cache()
        
        # Días que una película es considerada "nueva"
        self.new_threshold_days = NEW_THRESHOLD_DAYS
        
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

    def _load_uploads_cache(self):
        """Carga el registro de subidas"""
        try:
            if os.path.exists(self.uploads_file):
                with open(self.uploads_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando registro de subidas: {e}")
        return {}
    
    def _save_uploads_cache(self):
        """Guarda el registro de subidas"""
        try:
            with open(self.uploads_file, 'w', encoding='utf-8') as f:
                json.dump(self.uploads_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando registro de subidas: {e}")
    
    def register_upload(self, file_path):
        """Registra una nueva subida con timestamp"""
        try:
            file_name = os.path.basename(file_path)
            self.uploads_cache[file_name] = {
                'upload_time': time.time(),
                'file_path': file_path
            }
            self._save_uploads_cache()
            logger.info(f"📝 Subida registrada: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Error registrando subida: {e}")
            return False

    def invalidate_cache(self):
        """Invalida el caché del catálogo para forzar recarga"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("🗑️ Caché de catálogo eliminado")
        except Exception as e:
            logger.error(f"Error eliminando caché: {e}")
            
    def is_new_movie(self, file_name, file_time):
        """
        Determina si una película es nueva basado en:
        1. Si fue subida recientemente (registro de subidas)
        2. Si la fecha del archivo es reciente
        """
        # Verificar si está en el registro de subidas
        if file_name in self.uploads_cache:
            upload_time = self.uploads_cache[file_name]['upload_time']
            if time.time() - upload_time < self.new_threshold_days * 24 * 3600:
                return True, upload_time, 'upload'
        
        # Si no, usar la fecha del archivo
        if time.time() - file_time < self.new_threshold_days * 24 * 3600:
            return True, file_time, 'file'
        
        return False, None, None

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
        
        categorias_lista, series, total_videos = self._scan_files()
        
        scan_time = time.time() - start_time
        logger.info(f"✅ Escaneo completado en {scan_time:.2f} segundos: {total_videos} videos")
        
        # Guardar en caché (AHORA CON 3 ARGUMENTOS)
        self._save_cache(categorias_lista, series, total_videos)
        
        return categorias_lista, series

    def _scan_files(self):
        """Método privado que realiza el escaneo real del sistema de archivos"""
        categorias = {}
        series = {}
        novedades = []  # Lista para películas nuevas
        
        total_videos = 0
        thumbnails_faltantes = 0
        
        # Recopilar thumbnails existentes
        existing_thumbnails = self.thumbnail_processor.get_existing_thumbnails()
        
        # Fecha límite para novedades (usando threshold)
        cutoff_time = time.time() - (self.new_threshold_days * 24 * 3600)
        
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
                        
                        # Obtener fecha de creación/modificación del archivo
                        try:
                            file_stat = os.stat(full_path)
                            file_time = max(file_stat.st_ctime, file_stat.st_mtime)
                        except:
                            file_time = time.time()
                        
                        base_name = os.path.splitext(file)[0]
                        base_name = unicodedata.normalize('NFC', base_name)
                        clean_name = clean_filename(file)
                        
                        # Determinar si es nuevo
                        is_new, new_time, new_source = self.is_new_movie(os.path.basename(file), file_time)
                        
                        # Calcular días desde que es nuevo (para mostrar)
                        days_ago = None
                        if is_new and new_time:
                            days_ago = int((time.time() - new_time) / (24 * 3600))
                        
                        # Formatear fecha para mostrar
                        date_added = None
                        if new_time:
                            date_added = datetime.fromtimestamp(new_time).strftime("%d/%m/%Y")
                        
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
                            "thumbnail_pending": not has_thumbnail,
                            "is_new": is_new,
                            "days_ago": days_ago,
                            "date_added": date_added,
                            "timestamp": file_time  # Para ordenar por fecha
                        }

                        if "-serie" in file.lower():
                            series_name = clean_name.rsplit(" T", 1)[0] if " T" in clean_name else clean_name
                            if series_name not in series:
                                series[series_name] = []
                            series[series_name].append(item)
                        else:
                            # Añadir a novedades si es nueva
                            if is_new:
                                novedades.append(item)
                            
                            if categoria not in categorias:
                                categorias[categoria] = []
                            categorias[categoria].append(item)
                            
                except Exception as e:
                    logger.error(f"Error procesando archivo {file}: {e}")
                    continue

        # Ordenar novedades por fecha (más recientes primero)
        novedades.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Crear lista final con Novedades primero
        categorias_lista = []
        
        # Primero, añadir Novedades si existe (limitado a 20)
        if novedades:
            categorias_lista.append(("🆕 Recien Añadidas", novedades[:20]))
        
        # Añadir el resto de categorías ordenadas alfabéticamente
        for cat in sorted(categorias.keys()):
            categorias_lista.append((cat, sorted(categorias[cat], key=lambda x: x["name"])))
        
        # Ordenar series (siempre alfabéticamente)
        series = {
            k: sorted(v, key=lambda x: x["name"])
            for k, v in sorted(series.items())
        }

        logger.info(f"📊 Escaneo: {total_videos} videos, {thumbnails_faltantes} thumbnails pendientes, {len(novedades)} novedades")
        logger.info(f"📋 Orden de categorías (backend): {[cat for cat, _ in categorias_lista]}")

        return categorias_lista, series, total_videos

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