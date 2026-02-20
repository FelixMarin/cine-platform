# Procesador de thumbnails en segundo plano

import threading
import queue
import time
import os
from modules.media.constants import QUEUE_MAXSIZE, MAX_CONSECUTIVE_ERRORS, ERROR_SLEEP_TIME
from modules.media.ffmpeg_helper import (
    generate_thumbnail,
    check_ffmpeg_webp_support
)
from modules.media.utils import sanitize_for_log
from modules.logging.logging_config import setup_logging
import os as os_env

logger = setup_logging(os_env.environ.get("LOG_FOLDER"))


class ThumbnailProcessor:
    """Procesador de thumbnails en segundo plano"""
    
    def __init__(self, thumbnails_folder):
        self.thumbnails_folder = thumbnails_folder
        self.queued_thumbnails = set()
        self.thumbnail_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
        self.processing_thread = None
        self.processed_count = 0
        self.total_pending = 0
        self.processing_active = False
        self._lock = threading.Lock()
        
        # Asegurar que la carpeta de thumbnails existe
        if not os.path.exists(self.thumbnails_folder):
            os.makedirs(self.thumbnails_folder)
    
    def start(self):
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
                    success = generate_thumbnail(video_path, thumbnail_path)
                    
                    if success:
                        # Si hay soporte WebP, también generar versión WebP
                        if check_ffmpeg_webp_support():
                            webp_path = thumbnail_path.replace('.jpg', '.webp')
                            if not os.path.exists(webp_path):
                                generate_thumbnail(video_path, webp_path)
                        
                        self.processed_count += 1
                        consecutive_errors = 0
                        remaining = self.thumbnail_queue.qsize()
                        logger.info(f"✅ Thumbnail generado: {safe_base_name} (Pendientes: {remaining})")
                    else:
                        consecutive_errors += 1
                        logger.error(f"❌ Error generando {safe_base_name}")
                    
                    self.thumbnail_queue.task_done()
                    
                    # Si hay muchos errores consecutivos, esperar un poco
                    if consecutive_errors > MAX_CONSECUTIVE_ERRORS:
                        time.sleep(ERROR_SLEEP_TIME)
                        consecutive_errors = 0
                    
                except queue.Empty:
                    # No hay trabajo, actualizar contadores
                    with self._lock:
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
    
    def stop(self):
        """Detiene el procesador de thumbnails"""
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
    
    def queue_thumbnail(self, video_path, base_name):
        """Añade un thumbnail a la cola de procesamiento (evita duplicados)"""
        thumbnail_path = os.path.join(self.thumbnails_folder, f"{base_name}.jpg")
        
        # No encolar si ya existe
        if os.path.exists(thumbnail_path):
            return False
        
        # Verificar si ya está en cola
        with self._lock:
            if base_name in self.queued_thumbnails:
                return False
            
            self.queued_thumbnails.add(base_name)
            self.thumbnail_queue.put((video_path, thumbnail_path, base_name))
            self.total_pending += 1
        
        safe_base_name = sanitize_for_log(base_name)
        logger.debug(f"📝 Encolado thumbnail: {safe_base_name} (Cola: {self.thumbnail_queue.qsize()})")
        return True
    
    def get_status(self):
        """Devuelve el estado actualizado de la generación de thumbnails"""
        return {
            "queue_size": self.thumbnail_queue.qsize(),
            "total_pending": self.total_pending,
            "processed": self.processed_count,
            "processing": self.processing_thread is not None and self.processing_thread.is_alive()
        }
    
    def get_existing_thumbnails(self):
        """Recopila todos los thumbnails existentes"""
        existing = set()
        if os.path.exists(self.thumbnails_folder):
            for f in os.listdir(self.thumbnails_folder):
                if f.endswith('.jpg'):
                    existing.add(os.path.splitext(f)[0])
        return existing
