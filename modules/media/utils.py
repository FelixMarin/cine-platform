# Utilidades del módulo media

import unicodedata
import os
import re
from modules.media.constants import FILENAME_SUFFIXES_TO_REMOVE


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


def normalize_path(path):
    """Normaliza una ruta para manejar caracteres Unicode"""
    if isinstance(path, bytes):
        path = path.decode('utf-8', errors='replace')
    return unicodedata.normalize('NFC', path)


def clean_filename(filename):
    """Limpia y formatea nombres de archivo con soporte UTF-8"""
    try:
        if isinstance(filename, bytes):
            filename = filename.decode('utf-8', errors='replace')
        
        filename = unicodedata.normalize('NFC', filename)
        name = os.path.splitext(filename)[0]

        for suffix in FILENAME_SUFFIXES_TO_REMOVE:
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
        
    except Exception:
        return filename


def is_video_file(filename):
    """Determina si un archivo es un video basado en su extensión"""
    from modules.media.constants import VIDEO_EXTENSIONS
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS


def get_category_from_path(root, base_folder):
    """Obtiene la categoría desde una ruta relativa"""
    try:
        root = unicodedata.normalize('NFC', root)
        categoria = os.path.relpath(root, base_folder).replace("\\", "/")
        if isinstance(categoria, bytes):
            categoria = categoria.decode('utf-8', errors='replace')
        categoria = unicodedata.normalize('NFC', categoria)
    except:
        return None

    if categoria == "." or categoria.lower() == "thumbnails":
        categoria = "Sin categoría"

    return categoria


def extract_serie_name(filename: str, folder_name: str = None) -> str:
    """
    Extrae el nombre de la serie a partir del nombre del archivo o carpeta.
    
    Args:
        filename: Nombre del archivo (ej: "12 Monos T1C01-serie-optimized.mkv")
        folder_name: Nombre de la carpeta (ej: "12 Monos.S01")
    
    Returns:
        Nombre de la serie (ej: "12 Monos")
    """
    # Intentar extraer de la carpeta primero (más fiable)
    if folder_name:
        # Eliminar .S01, .S02, .Season1, y también "Temporada X"
        serie = re.sub(r'\.S\d{2}', '', folder_name)
        serie = re.sub(r'\.Season\d+', '', serie, flags=re.IGNORECASE)
        serie = re.sub(r'Temporada\s*\d+', '', serie, flags=re.IGNORECASE)
        # Reemplazar puntos y guiones por espacios
        serie = serie.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        # Eliminar espacios múltiples
        serie = re.sub(r'\s+', ' ', serie).strip()
        return serie
    
    # Si no hay carpeta, extraer del nombre del archivo
    # Eliminar patrones como T1C01, -serie, -optimized
    name = filename.replace('-serie', '').replace('-optimized', '').replace('_optimized', '')
    name = re.sub(r'[Tt]\d+[Cc]\d+', '', name)  # Eliminar T1C01, T01C01, etc.
    name = re.sub(r'\.\w+$', '', name)  # Eliminar extensión
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name
    

def clean_movie_title(title: str) -> str:
    """
    Limpia el título de una película eliminando sufijos y fechas.
    
    Args:
        title: Título original (ej: "Multiple-(2016)-optimized")
    
    Returns:
        Título limpio (ej: "Multiple")
    """
    if not title:
        return title
    
    logger.debug(f"🧹 Limpiando título: '{title}'")
    
    # Paso 1: Eliminar sufijos
    clean = title.replace('-optimized', '').replace('_optimized', '')
    logger.debug(f"   Después de quitar sufijos: '{clean}'")
    
    # Paso 2: Eliminar fecha (YYYY)
    clean = re.sub(r'\(\d{4}\)', '', clean)
    logger.debug(f"   Después de quitar fecha: '{clean}'")
    
    # Paso 3: Limpiar espacios y guiones
    clean = clean.replace('-', ' ').replace('_', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    logger.debug(f"✅ Título limpio: '{clean}'")
    
    return clean

def get_serie_poster_cache_key(serie_name: str) -> str:
    """Genera clave de caché para el póster de una serie"""
    return f"serie_poster_{serie_name.replace(' ', '_').lower()}"