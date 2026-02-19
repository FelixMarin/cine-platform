# Utilidades del módulo media

import unicodedata
import os
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
