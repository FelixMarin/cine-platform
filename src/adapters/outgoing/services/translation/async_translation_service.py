"""
Servicio de traducción asíncrona con hilos en background
Implementa:
- Respuesta inmediata (< 500ms)
- Traducción en hilo separado (no bloqueante)
- Persistencia en BD (plot_es)
- Lock para evitar traducciones duplicadas
- Logging para monitoreo
"""
import os
import logging
import hashlib
import threading
import time
from typing import Optional, Dict, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# === LOCKS Y CACHÉS GLOBALES ===

# Lock global para evitar traducciones duplicadas simultáneas
_translation_locks: Dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()

# Caché de traducciones completadas (en memoria)
_translated_cache: Dict[Tuple[str, str], str] = {}

# Caché de traducciones en progreso (para no lanzar duplicadas)
_translations_in_progress: Dict[str, threading.Event] = {}


def _get_text_hash(text: str) -> str:
    """Genera un hash corto del texto para logging"""
    return hashlib.md5(text.encode()).hexdigest()[:8]


def _get_cache_key(plot: str, title: str = None) -> Tuple[str, str]:
    """Genera una clave de caché basada en el texto y título"""
    text_hash = _get_text_hash(plot)
    title_key = title if title else "unknown"
    return (text_hash, title_key)


def _get_title_lock_key(title: str) -> str:
    """Genera una clave única para el lock por título de película"""
    return f"translate_{title.lower().strip()}"


def _acquire_translation_lock(title: str) -> Tuple[bool, threading.Lock]:
    """
    Adquiere un lock para una traducción específica.
    Retorna (éxito, lock)
    """
    lock_key = _get_title_lock_key(title)
    
    with _locks_lock:
        if lock_key not in _translation_locks:
            _translation_locks[lock_key] = threading.Lock()
        
        lock = _translation_locks[lock_key]
    
    # Intentar adquirir el lock sin bloquear
    acquired = lock.acquire(blocking=False)
    return acquired, lock


def _release_translation_lock(title: str):
    """Libera el lock de traducción"""
    lock_key = _get_title_lock_key(title)
    
    with _locks_lock:
        if lock_key in _translation_locks:
            try:
                _translation_locks[lock_key].release()
            except RuntimeError:
                # Lock no estaba adquirido o ya liberado
                pass


def _get_cached_translation(plot: str, title: str = None) -> Optional[str]:
    """
    Obtiene una traducción del caché si existe.
    Returns None si no hay traducción cacheada.
    """
    cache_key = _get_cache_key(plot, title)
    
    if cache_key in _translated_cache:
        text_hash = _get_text_hash(plot)
        logger.debug(f"✅ Translation cache HIT para '{title}' (hash: {text_hash})")
        return _translated_cache[cache_key]
    
    return None


def _save_translation_to_cache(plot: str, translated_plot: str, title: str = None):
    """Guarda una traducción completada en el caché"""
    cache_key = _get_cache_key(plot, title)
    _translated_cache[cache_key] = translated_plot
    text_hash = _get_text_hash(plot)
    logger.info(f"💾 Translation guardada en cache para '{title}' (hash: {text_hash})")


def _save_translation_to_database(title: str, translated_plot: str):
    """
    Guarda la traducción en la base de datos (tabla omdb_entries, campo plot_es).
    """
    try:
        from src.adapters.outgoing.repositories.postgresql.catalog_repository import CatalogRepository
        
        repo = CatalogRepository()
        # Buscar por título para encontrar el imdb_id
        entries = repo.search_omdb_entries(title, limit=1)
        
        if entries:
            # Usar el primer resultado (más relevante)
            entry = entries[0]
            if entry.imdb_id:
                repo.update_plot_es(entry.imdb_id, translated_plot)
                logger.info(f"💾 [DB] plot_es guardado en BD para '{title}' (imdb_id: {entry.imdb_id})")
            else:
                logger.warning(f"⚠️ [DB] Entry '{title}' no tiene imdb_id, no se puede guardar plot_es")
        else:
            logger.warning(f"⚠️ [DB] No se encontró entrada en BD para '{title}'")
            
    except Exception as e:
        logger.error(f"❌ [DB] Error guardando plot_es en BD: {e}")
        # No fallar la traducción por error de BD


def _translate_in_background(plot: str, title: str):
    """
    Función que se ejecuta en un hilo separado para traducir el plot.
    Esta función es llamada por el hilo daemon.
    """
    start_time = time.time()
    text_hash = _get_text_hash(plot)
    
    try:
        logger.info(f"🔄 [BACKGROUND] Iniciando traducción asíncrona de '{title}' (hash: {text_hash})")
        
        # Importar el servicio de traducción existente
        from src.adapters.outgoing.services.translation.translation_service import get_translation_service
        
        service = get_translation_service()
        translated_plot, was_translated = service.translate(plot, title)
        
        elapsed = time.time() - start_time
        
        if was_translated and translated_plot:
            # Guardar en caché en memoria
            _save_translation_to_cache(plot, translated_plot, title)
            
            # Guardar en BD (persistencia)
            _save_translation_to_database(title, translated_plot)
            
            logger.info(f"✅ [BACKGROUND] Traducción completada para '{title}' en {elapsed:.2f}s")
        else:
            logger.warning(f"⚠️ [BACKGROUND] Traducción no realizada para '{title}' (was_translated={was_translated})")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ [BACKGROUND] Error en traducción asíncrona de '{title}': {e} (tiempo: {elapsed:.2f}s)")
    
    finally:
        # Siempre liberar el lock
        _release_translation_lock(title)


# === FUNCIONES PÚBLICAS ===

def get_plot_es_from_database(title: str) -> Optional[str]:
    """
    Obtiene el plot_es (traducido) desde la base de datos.
    
    Args:
        title: Título de la película/serie
        
    Returns:
        Plot traducido al español o None si no existe
    """
    try:
        from src.adapters.outgoing.repositories.postgresql.catalog_repository import CatalogRepository
        
        repo = CatalogRepository()
        entries = repo.search_omdb_entries(title, limit=5)
        
        # Buscar una entrada que tenga plot_es
        for entry in entries:
            # Verificar que la columna existe y tiene valor
            if hasattr(entry, 'plot_es') and entry.plot_es:
                logger.info(f"✅ [DB] plot_es encontrado en BD para '{title}' (id: {entry.id})")
                return entry.plot_es
        
        return None
        
    except Exception as e:
        logger.error(f"❌ [DB] Error obteniendo plot_es de BD: {e}")
        return None


def translate_plot_async(plot: str, title: str = None) -> Tuple[str, bool, bool]:
    """
    Función principal de traducción asíncrona.
    
    COMPORTAMIENTO:
    1. Si hay traducción en BD (plot_es), retornarla INMEDIATAMENTE
    2. Si hay traducción cacheada en memoria, retornarla
    3. Si no hay traducción pero hay un lock activo, retornar original (ya se está traduciendo)
    4. Si no hay traducción ni lock, iniciar traducción en background y retornar original
    
    Args:
        plot: Texto del plot a traducir (en inglés)
        title: Título de la película (para lock y cache)
        
    Returns:
        Tupla (plot_a_retornar, fue_traducido, translation_iniciada)
        - plot_a_retornar: plot original o traducido
        - fue_traducido: True si se retornó una traducción
        - translation_iniciada: True si se inició traducción en background
    """
    # Validaciones iniciales
    if not plot or len(plot.strip()) < 10:
        return plot, False, False
    
    # 1. Verificar si hay traducción en BD (prioridad máxima - persistente)
    if title:
        db_translation = get_plot_es_from_database(title)
        if db_translation:
            # Guardar en caché para futuras referencias
            _save_translation_to_cache(plot, db_translation, title)
            return db_translation, True, False
    
    # 2. Verificar si hay traducción en caché en memoria
    cached_translation = _get_cached_translation(plot, title)
    if cached_translation:
        return cached_translation, True, False
    
    # 3. Intentar adquirir lock para iniciar traducción
    if title:
        acquired, lock = _acquire_translation_lock(title)
        
        if acquired:
            # Somos responsables de iniciar la traducción
            # Iniciar hilo daemon (no bloqueante)
            thread = threading.Thread(
                target=_translate_in_background,
                args=(plot, title),
                daemon=True  # El hilo morirá cuando el proceso principal muera
            )
            thread.start()
            
            logger.info(f"🚀 [ASYNC] Hilo de traducción iniciado para '{title}'")
            
            # Retornar plot original mientras la traducción ocurre en background
            return plot, False, True
        else:
            # Otra traducción ya está en progreso para esta película
            logger.info(f"⏳ [ASYNC] Traducción ya en progreso para '{title}', retornando original")
            return plot, False, False
    else:
        # Sin título, no podemos hacer tracking, retornamos original
        logger.warning("⚠️ [ASYNC] No se puede iniciar traducción sin título")
        return plot, False, False


def translate_plot_background_only(plot: str, title: str = None) -> Tuple[str, bool]:
    """
    Versión simplificada que solo retorna el plot (traducido o no)
    sin indicar si se inició traducción.
    
    Útil para endpoints que no necesitan saber si hay traducción en curso.
    """
    result, was_translated, _ = translate_plot_async(plot, title)
    return result, was_translated


# === FUNCIONES DE DIAGNÓSTICO ===

def get_translation_cache_stats() -> dict:
    """Retorna estadísticas del caché de traducciones"""
    return {
        "cache_size": len(_translated_cache),
        "active_locks": len(_translation_locks),
    }


def clear_translation_cache():
    """Limpia el caché de traducciones (para testing)"""
    global _translated_cache
    _translated_cache = {}
    logger.info("🗑️ Caché de traducciones limpiado")
