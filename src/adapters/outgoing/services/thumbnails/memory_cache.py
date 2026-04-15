"""
Caché en memoria para thumbnails

Responsabilidad: Almacenar thumbnails en memoria RAM para evitar
saturación del pool de conexiones a la base de datos.
"""

import logging
import re
import time
from threading import Lock
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MemoryThumbnailCache:
    """
    Caché en memoria para thumbnails con TTL.
    Reduce drásticamente las consultas a base de datos.
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Inicializa el caché en memoria.
        
        Args:
            ttl_seconds: Tiempo de vida de cada entrada en segundos (default 1 hora)
        """
        self.cache: Dict[str, dict] = {}
        self.lock = Lock()
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
        logger.info(f"✅ MemoryThumbnailCache inicializado con TTL={ttl_seconds}s")

    def get_cache_key(self, title: str, year: Optional[str]) -> str:
        """
        Genera clave de caché normalizada.
        
        Args:
            title: Título de la película
            year: Año (opcional)
            
        Returns:
            Clave normalizada para el caché
        """
        # Limpiar título: minúsculas, sin caracteres especiales
        clean_title = re.sub(r'[^a-z0-9]', '_', title.lower())
        # Quitar guiones bajos consecutivos
        clean_title = re.sub(r'_+', '_', clean_title)
        # Quitar guiones bajos al inicio y final
        clean_title = clean_title.strip('_')

        year_str = str(year) if year else 'unknown'
        return f"{clean_title}_{year_str}"

    def get(self, title: str, year: Optional[str]) -> Optional[bytes]:
        """
        Obtiene thumbnail de caché si existe y no ha expirado.
        
        Args:
            title: Título de la película
            year: Año (opcional)
            
        Returns:
            Datos binarios del thumbnail o None si no está en caché
        """
        key = self.get_cache_key(title, year)

        with self.lock:
            entry = self.cache.get(key)
            if entry:
                if time.time() - entry['timestamp'] < self.ttl:
                    self.hits += 1
                    logger.info(f"✅ Caché HIT para {title} ({year})")
                    return entry['data']
                else:
                    # Expirado, eliminar
                    del self.cache[key]
                    logger.info(f"⏰ Caché EXPIRADO para {title} ({year})")

            self.misses += 1
            logger.info(f"❌ Caché MISS para {title} ({year})")
            return None

    def set(self, title: str, year: Optional[str], data: bytes):
        """
        Guarda thumbnail en caché.
        
        Args:
            title: Título de la película
            year: Año (opcional)
            data: Datos binarios del thumbnail
        """
        key = self.get_cache_key(title, year)

        with self.lock:
            self.cache[key] = {
                'data': data,
                'timestamp': time.time(),
                'title': title,
                'year': year
            }
            logger.info(f"💾 Caché SET para {title} ({year}) - {len(data)} bytes")

    def clear(self):
        """Limpia toda la caché (útil para tests o mantenimiento)"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("🧹 Caché limpiada manualmente")

    def get_stats(self) -> dict:
        """
        Obtiene estadísticas de uso del caché.
        
        Returns:
            Diccionario con tamaño, hits, misses y ratio de aciertos
        """
        with self.lock:
            total = self.hits + self.misses
            return {
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'hit_ratio': self.hits / total if total > 0 else 0
            }

    def cleanup_expired(self):
        """Elimina entradas expiradas del caché."""
        current_time = time.time()
        expired_keys = []

        with self.lock:
            for key, entry in self.cache.items():
                if current_time - entry['timestamp'] >= self.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]

        if expired_keys:
            logger.info(f"🧹 Eliminadas {len(expired_keys)} entradas expiradas del caché")


# Instancia global única (singleton)
_thumbnail_cache: Optional[MemoryThumbnailCache] = None


def get_thumbnail_cache() -> MemoryThumbnailCache:
    """
    Factory para obtener la instancia única de caché.
    
    Returns:
        Instancia de MemoryThumbnailCache
    """
    global _thumbnail_cache
    if _thumbnail_cache is None:
        _thumbnail_cache = MemoryThumbnailCache(ttl_seconds=3600)
    return _thumbnail_cache
