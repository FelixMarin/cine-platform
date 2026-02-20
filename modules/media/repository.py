# Repositorio de medios - Implementación del sistema de archivos

import os
import unicodedata
import threading
import json
import time
import re
from collections import OrderedDict
from datetime import datetime
from modules.core import IMediaRepository
from modules.media.constants import VIDEO_EXTENSIONS, CACHE_TTL, CACHE_FILE, NEW_THRESHOLD_DAYS, UPLOADS_CACHE_FILE
from modules.media.utils import (
    normalize_path,
    clean_filename,
    is_video_file,
    get_category_from_path,
    sanitize_for_log,
    extract_serie_name
)
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
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Archivo de caché corrupto, eliminando: {e}")
            try:
                os.remove(self.cache_file)
            except:
                pass
            return None
        except Exception as e:
            logger.error(f"Error cargando caché: {e}")
            return None

    def _save_cache(self, categorias, series, total_videos):
        """Guarda el catálogo en caché con manejo de caracteres especiales"""
        try:
            # Función para limpiar strings problemáticos
            def clean_for_json(obj):
                if isinstance(obj, str):
                    # Reemplazar caracteres surrogados
                    return obj.encode('utf-8', errors='ignore').decode('utf-8')
                elif isinstance(obj, dict):
                    return {clean_for_json(k): clean_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_for_json(item) for item in obj]
                else:
                    return obj
            
            cache_data = {
                'categorias': clean_for_json(categorias),
                'series': clean_for_json(series),
                'total_videos': total_videos,
                'timestamp': time.time()
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 {total_videos} videos guardados en caché")
        except Exception as e:
            logger.error(f"Error guardando caché: {e}")
            # Intentar guardar sin indent para ver si es problema de formato
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False)
                logger.info(f"💾 {total_videos} videos guardados en caché (sin indent)")
            except:
                pass

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
        
        # Escaneo completo
        logger.info("🔍 Escaneando archivos... (puede tardar unos segundos)")
        start_time = time.time()
        
        categorias_lista, series, total_videos = self._scan_files()
        
        scan_time = time.time() - start_time
        logger.info(f"✅ Escaneo completado en {scan_time:.2f} segundos: {total_videos} videos")
        
        # Guardar en caché
        self._save_cache(categorias_lista, series, total_videos)
        
        return categorias_lista, series

    def _extract_year_from_filename(self, filename: str) -> int:
        """Extrae el año del nombre del archivo si existe entre paréntesis"""
        year_match = re.search(r'\((\d{4})\)', filename)
        return int(year_match.group(1)) if year_match else None

    def _scan_files(self):
        """Método privado que realiza el escaneo real del sistema de archivos"""
        categorias = {}
        series = {}
        novedades = []  # Lista para películas nuevas
        
        total_videos = 0
        
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
                        
                        # Extraer año del nombre del archivo
                        year = self._extract_year_from_filename(file)
                        
                        # Limpiar nombre para mostrar (sin año ni sufijos)
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
                        
                        # Construir item SIN thumbnails locales
                        item = {
                            "name": clean_name,  # Nombre limpio para mostrar
                            "filename": base_name,  # Nombre original del archivo (con año)
                            "path": relative_path,
                            "year": year,  # Año extraído para búsqueda en OMDB
                            "is_new": is_new,
                            "days_ago": days_ago,
                            "date_added": date_added,
                            "timestamp": file_time,  # Para ordenar por fecha
                            # Sin campos de thumbnail - se cargarán desde OMDB
                        }

                        if "-serie" in file.lower():
                            # Extraer nombre de serie
                            serie_name = extract_serie_name(file, os.path.basename(root))
                            
                            item = {
                                "name": clean_name,
                                "serie_name": serie_name,  # Nombre de la serie para buscar póster
                                "path": relative_path,
                                "year": year,
                                "is_new": is_new,
                                "days_ago": days_ago,
                                "date_added": date_added,
                                "timestamp": file_time,
                                "is_serie": True  # Flag para identificar series
                            }
                            
                            if serie_name not in series:
                                series[serie_name] = []
                            series[serie_name].append(item)
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

        logger.info(f"📊 Escaneo: {total_videos} videos, {len(novedades)} novedades")
        logger.info(f"📋 Orden de categorías (backend): {[cat for cat, _ in categorias_lista]}")

        return categorias_lista, series, total_videos

    def get_thumbnails_folder(self):
        """Devuelve la carpeta de thumbnails (compatibilidad)"""
        return os.path.join(self.movies_folder, "thumbnails")

    def get_safe_path(self, filename):
        """Valida rutas para prevenir path traversal"""
        if not self.is_path_safe(filename):
            return None
        
        filename = unicodedata.normalize("NFC", filename)
        base_dir = os.path.abspath(self.movies_folder)
        target_path = os.path.abspath(os.path.join(base_dir, filename))
        return target_path

    # Métodos de compatibilidad eliminados:
    # - get_thumbnail_status (ya no aplica)
    # - get_thumbnails_folder (ya no aplica)
    # - Métodos de ffmpeg_helper (se eliminan)