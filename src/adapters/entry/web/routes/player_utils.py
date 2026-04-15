"""
Utilidades para el reproductor
"""

import os
import re


def clean_filename(filename):
    """Limpia el nombre del archivo para mostrar"""
    name = re.sub(r"[-_]?optimized", "", filename, flags=re.IGNORECASE)
    name = re.sub(r"\.(mkv|mp4|avi|mov)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[._-]", " ", name)
    return " ".join(word.capitalize() for word in name.split())


def extract_year_from_filename(filename):
    """Extrae el año de un nombre de archivo"""
    year_match = re.search(r"\((\d{4})\)", filename)
    if year_match:
        return int(year_match.group(1))
    return None


def extract_clean_title(filename):
    """Extrae el título limpio de un nombre de archivo"""
    clean_title = re.sub(r"\(.*?\)", "", filename)
    clean_title = re.sub(r"[-_]?optimized", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\.(mkv|mp4|avi|mov)$", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"[._-]", " ", clean_title).strip()
    return clean_title


def get_media_info(filename):
    """
    Obtiene información completa de un archivo multimedia.

    Returns:
        dict con keys: basename, sanitized_name, year, clean_title
    """
    basename = os.path.basename(filename)
    return {
        "basename": basename,
        "sanitized_name": clean_filename(basename),
        "year": extract_year_from_filename(basename),
        "clean_title": extract_clean_title(basename),
    }
