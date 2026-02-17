import os
import subprocess
import threading
import queue
import time
import unicodedata
from modules.core import IMediaRepository
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

def sanitize_for_log(text):
    """Limpia caracteres problemáticos para logging"""
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize('NFC', text)
    text = ''.join(c if not '\ud800' <= c <= '\udfff' else '?' for c in text)
    try:
        text = text.encode('utf-8', errors='replace').decode('utf-8')
    except:
        text = text.encode('ascii', errors='replace').decode('ascii')
    return text

class FileSystemMediaRepository(IMediaRepository):
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
        
        if not os.path.exists(self.thumbnails_folder):
            os.makedirs(self.thumbnails_folder)
        
        # Conjunto para trackear qué thumbnails ya están encolados
        self.queued_thumbnails = set()
        self.thumbnail_queue = queue.Queue()
        self.processing_thread = None
        self.processed_count = 0
        self.total_pending = 0
        self.processing_active = False
        self._initialized = True
        
        self._start_background_processor()

    def get_movies_folder(self):
        """Devuelve la carpeta base de películas"""
        return self.movies_folder

    def is_path_safe(self, requested_path):
        """
        Verifica que una ruta solicitada está dentro de la carpeta base permitida
        """
        if not requested_path:
            return False
        
        try:
            # Normalizar rutas
            abs_requested = os.path.abspath(requested_path)
            abs_base = os.path.abspath(self.movies_folder)
            
            # Verificar que la ruta solicitada está dentro de la carpeta base
            return os.path.commonpath([abs_requested, abs_base]) == abs_base
        except Exception as e:
            logger.error(f"Error validando ruta: {e}")
            return False

    def _start_background_processor(self):
        """Inicia el thread de procesamiento en segundo plano"""
        if self.processing_active:
            return
            
        self.processing_active = True
        
        def process_queue():
            logger.info("🧵 Procesador de thumbnails iniciado")
            consecutive_errors = 0
            
            while self.processing_active:
                try:
                    # Obtener trabajo de la cola con timeout
                    video_path, thumbnail_path, base_name = self.thumbnail_queue.get(timeout=1)
                    
                    # Verificar si realmente necesitamos generar
                    if os.path.exists(thumbnail_path):
                        logger.debug(f"⏭️ Thumbnail ya existe, saltando: {sanitize_for_log(base_name)}")
                        self.thumbnail_queue.task_done()
                        continue
                    
                    safe_base_name = sanitize_for_log(base_name)
                    logger.info(f"🎬 Generando thumbnail: {safe_base_name}")
                    
                    # Generar thumbnail
                    success = self._generate_thumbnail(video_path, thumbnail_path)
                    
                    if success:
                        # Si hay soporte WebP, también generar versión WebP
                        if self._check_ffmpeg_webp_support():
                            webp_path = thumbnail_path.replace('.jpg', '.webp')
                            if not os.path.exists(webp_path):
                                self._generate_thumbnail(video_path, webp_path)
                        
                        self.processed_count += 1
                        consecutive_errors = 0
                        remaining = self.thumbnail_queue.qsize()
                        logger.info(f"✅ Thumbnail generado: {safe_base_name} (Pendientes: {remaining})")
                        
                        # Limpiar del conjunto de encolados
                        with threading.Lock():
                            if base_name in self.queued_thumbnails:
                                self.queued_thumbnails.remove(base_name)
                    else:
                        consecutive_errors += 1
                        logger.error(f"❌ Error generando {safe_base_name}")
                    
                    self.thumbnail_queue.task_done()
                    
                    # Si hay muchos errores consecutivos, esperar un poco
                    if consecutive_errors > 5:
                        logger.warning("⚠️ Múltiples errores, pausando 5 segundos...")
                        time.sleep(5)
                        consecutive_errors = 0
                    
                except queue.Empty:
                    # No hay trabajo, actualizar contadores
                    with threading.Lock():
                        if self.total_pending > 0 and self.thumbnail_queue.qsize() == 0:
                            self.total_pending = 0
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error en procesador: {sanitize_for_log(str(e))}")
                    time.sleep(1)
            
            logger.info("🛑 Procesador de thumbnails detenido")

        self.processing_thread = threading.Thread(target=process_queue, daemon=True)
        self.processing_thread.start()
        logger.info("📸 Procesador de thumbnails en segundo plano iniciado")

    def _queue_thumbnail_generation(self, video_path, base_name):
        """Añade un thumbnail a la cola de procesamiento (evita duplicados)"""
        thumbnail_path = os.path.join(self.thumbnails_folder, f"{base_name}.jpg")
        
        # No encolar si ya existe
        if os.path.exists(thumbnail_path):
            return False
        
        # Verificar si ya está en cola
        with threading.Lock():
            if base_name in self.queued_thumbnails:
                return False
            
            self.queued_thumbnails.add(base_name)
            self.thumbnail_queue.put((video_path, thumbnail_path, base_name))
            self.total_pending += 1
            
        safe_base_name = sanitize_for_log(base_name)
        logger.debug(f"📝 Encolado thumbnail: {safe_base_name} (Cola: {self.thumbnail_queue.qsize()})")
        return True

    def _check_ffmpeg_webp_support(self):
        """Verifica si ffmpeg soporta WebP"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return "libwebp" in result.stdout
        except:
            return False

    def _generate_thumbnail(self, video_path, thumbnail_path):
        """Genera un thumbnail en la ruta especificada - VERSIÓN SEGURA"""
        try:
            # Verificar que el video existe
            if not os.path.exists(video_path):
                logger.error(f"Video no encontrado: {video_path}")
                return False
            
            # Verificar que la ruta del thumbnail está dentro de la carpeta permitida
            if not self.is_path_safe(video_path):
                logger.error(f"Ruta de video no permitida: {video_path}")
                return False
            
            # Obtener duración del video
            duration = self._get_video_duration(video_path)
            
            if duration and duration > 60:
                capture_time = min(120, int(duration * 0.1))
            else:
                capture_time = 5
            
            hours = capture_time // 3600
            minutes = (capture_time % 3600) // 60
            seconds = capture_time % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            use_webp = thumbnail_path.endswith('.webp')
            
            # CONSTRUCCIÓN SEGURA: Siempre usar lista, NUNCA shell=True
            base_cmd = [
                "ffmpeg", 
                "-y",
                "-i", video_path,
                "-ss", time_str,
                "-vframes", "1",
                "-vf", "scale=320:-1",
            ]
            
            if use_webp:
                cmd = base_cmd + [
                    "-c:v", "libwebp",
                    "-lossless", "0",
                    "-compression_level", "6",
                    "-q:v", "75",
                    "-preset", "picture",
                    thumbnail_path
                ]
            else:
                cmd = base_cmd + [
                    "-q:v", "5",
                    "-pix_fmt", "yuvj420p",
                    thumbnail_path
                ]
            
            # Ejecutar con timeout - usando lista (seguro)
            result = subprocess.run(
                cmd, 
                check=True, 
                timeout=30,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout generando thumbnail para {video_path}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ffmpeg para {video_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return False

    def _get_video_duration(self, video_path):
        """Obtiene la duración del video en segundos usando ffprobe - VERSIÓN SEGURA"""
        try:
            # Verificar que la ruta es segura
            if not self.is_path_safe(video_path):
                logger.error(f"Ruta no permitida para obtener duración: {video_path}")
                return None
            
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=10,
                check=False  # No usar check=True para manejar errores
            )
            
            if result.returncode != 0:
                logger.error(f"Error en ffprobe: {result.stderr}")
                return None
                
            duration = float(result.stdout.strip())
            return duration
        except ValueError:
            logger.error(f"Error convirtiendo duración a float: {result.stdout}")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout obteniendo duración de {video_path}")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo duración: {e}")
            return None

    def _clean_filename(self, filename):
        """Limpia y formatea nombres de archivo con soporte UTF-8"""
        try:
            if isinstance(filename, bytes):
                filename = filename.decode('utf-8', errors='replace')
            
            filename = unicodedata.normalize('NFC', filename)
            name = os.path.splitext(filename)[0]

            for suffix in ["-optimized", "_optimized", "-serie"]:
                if name.lower().endswith(suffix):
                    name = name[: -len(suffix)]

            name = name.replace("-", " ").replace("_", " ").replace(".", " ")

            def smart_cap(word):
                if not word:
                    return word
                first = word[0].upper()
                rest = word[1:].lower() if len(word) > 1 else ""
                return first + rest

            words = []
            for w in name.split():
                if any(c.isdigit() for c in w):
                    words.append(smart_cap(w))
                else:
                    words.append(w.capitalize())
            
            result = " ".join(words)
            result = unicodedata.normalize('NFC', result)
            return result
            
        except Exception as e:
            logger.error(f"Error limpiando nombre: {e}")
            return filename

    def list_content(self):
        """Lista todo el contenido SIN re-encolar thumbnails existentes"""
        categorias = {}
        series = {}
        
        total_videos = 0
        thumbnails_faltantes = 0
        
        # Primero, recopilar todos los thumbnails existentes
        existing_thumbnails = set()
        if os.path.exists(self.thumbnails_folder):
            for f in os.listdir(self.thumbnails_folder):
                if f.endswith('.jpg'):
                    existing_thumbnails.add(os.path.splitext(f)[0])
        
        for root, _, files in os.walk(self.movies_folder):
            try:
                root = unicodedata.normalize('NFC', root)
                categoria = os.path.relpath(root, self.movies_folder).replace("\\", "/")
                if isinstance(categoria, bytes):
                    categoria = categoria.decode('utf-8', errors='replace')
                categoria = unicodedata.normalize('NFC', categoria)
            except:
                continue

            if categoria == "." or categoria.lower() == "thumbnails":
                categoria = "Sin categoría"

            for file in files:
                try:
                    if isinstance(file, bytes):
                        file = file.decode('utf-8', errors='replace')
                    file = unicodedata.normalize('NFC', file)
                    
                    if file.endswith(('.mkv', '.mp4', '.avi')):
                        total_videos += 1
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, self.movies_folder).replace("\\", "/")
                        
                        base_name = os.path.splitext(file)[0]
                        base_name = unicodedata.normalize('NFC', base_name)
                        clean_name = self._clean_filename(file)
                        
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

        logger.info(f"📊 Escaneo: {total_videos} videos, {thumbnails_faltantes} thumbnails pendientes")

        return categorias, series

    def get_thumbnail_status(self):
        """Devuelve el estado actualizado de la generación de thumbnails"""
        return {
            "queue_size": self.thumbnail_queue.qsize(),
            "total_pending": self.total_pending,
            "processed": self.processed_count,
            "processing": self.processing_thread is not None and self.processing_thread.is_alive()
        }

    def get_safe_path(self, filename):
        """Valida rutas para prevenir path traversal"""
        base_dir = os.path.abspath(self.movies_folder)
        target_path = os.path.abspath(os.path.join(base_dir, filename))
        
        if not target_path.startswith(base_dir):
            logger.warning(f"ALERTA: Path Traversal: {filename}")
            return None
        return target_path
    
    def get_thumbnails_folder(self):
        return self.thumbnails_folder