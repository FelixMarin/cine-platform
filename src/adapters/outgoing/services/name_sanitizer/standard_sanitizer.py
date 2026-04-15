"""
Implementación de INameSanitizer para sanitizar nombres de archivos
"""

import logging
import os
import re
import unicodedata

from src.domain.ports.out.services.INameSanitizer import INameSanitizer

logger = logging.getLogger(__name__)


class StandardSanitizer(INameSanitizer):
    """
    Sanitizador estándar de nombres de archivos de películas

    Formato de salida: nombre-de-pelicula-(año)-optimized.mkv

    Reglas:
    1. Conservar el año entre paréntesis (2025) → debe mantenerse igual
    2. Eliminar todo lo que esté entre corchetes [...] (calidad, idioma, etc.)
    3. Eliminar palabras como: Bluray, HDTV, WEB-DL, 720p, 1080p, 4K, Esp, Ing, etc.
    4. Convertir a minúsculas
    5. Reemplazar espacios por guiones
    6. Eliminar acentos (á → a, é → e, etc.)
    7. Añadir sufijo -optimized al final

    Ejemplos:
    - "28 años después El templo de los huesos (2026) [Bluray 720p][Esp].mkv" -> "28-anos-despues-el-templo-de-los-huesos-(2026)-optimized.mkv"
    - "Jurassic World El renacer (2025) [Bluray 720p][Esp].mkv" -> "jurassic-world-el-renacer-(2025)-optimized.mkv"
    - "The Movie (2024) [4K HDR][Ing].mkv" -> "the-movie-(2024)-optimized.mkv"
    """

    def sanitize(self, filename: str) -> str:
        """
        Sanitiza el nombre del archivo según el estándar:
        nombre-de-pelicula-(año)-optimized.mkv

        Args:
            filename: Nombre original del archivo (ej: "28 años después... (2026) [Bluray][Esp].mkv")

        Returns:
            Nombre sanitizado (ej: "28-anos-despues-el-templo-de-los-huesos-(2026)-optimized.mkv")
        """
        # 1. Extraer nombre base sin extensión
        base = os.path.splitext(filename)[0]

        # 2. Extraer y CONSERVAR el año entre paréntesis
        year_match = re.search(r'\((\d{4})\)', base)
        year = year_match.group(0) if year_match else ''  # Conservar con paréntesis: "(2025)"

        # 3. Eliminar el año temporalmente para procesar el título
        if year:
            base = base.replace(year, '')

        # 4. Eliminar todo lo que está entre corchetes [ ... ]
        base = re.sub(r'\[[^\]]*\]', '', base)

        # 5. Eliminar palabras comunes de calidad/idioma (que no estén entre paréntesis)
        quality_patterns = [
            r'\bBluray\b', r'\bHDTV\b', r'\bWEB-DL\b', r'\bWEBRip\b', r'\bDVD\b', r'\bHDRip\b', r'\bBDRip\b',
            r'\b720p\b', r'\b1080p\b', r'\b2160p\b', r'\b4K\b', r'\bUHD\b',
            r'\bEsp\b', r'\bIng\b', r'\bCastellano\b', r'\bVO\b', r'\bVOSE\b', r'\bSubtitulado\b',
            r'\bx264\b', r'\bx265\b', r'\bHEVC\b', r'\bAVC\b', r'\bH\.?264\b', r'\bH\.?265\b',
        ]

        for pattern in quality_patterns:
            base = re.sub(pattern, '', base, flags=re.IGNORECASE)

        # 6. Limpiar espacios extras y caracteres especiales
        base = re.sub(r'\s+', ' ', base)  # Múltiples espacios → un espacio
        base = re.sub(r'[^\w\s-]', '', base)  # Eliminar puntuación

        # 7. Eliminar acentos
        base = unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode('utf-8')

        # 8. Reemplazar espacios por guiones y convertir a minúsculas
        base = re.sub(r'\s+', '-', base.strip()).lower()

        # 9. Añadir el año (con paréntesis) si existe
        if year:
            base = f"{base}-{year}"

        # 10. Eliminar posibles guiones dobles
        base = re.sub(r'-+', '-', base)

        # 11. Añadir sufijo -optimized y extensión
        result = f"{base}-optimized.mkv"

        # 12. Limpieza final
        result = re.sub(r'-+', '-', result)

        logger.info(f"[StandardSanitizer] Original: {filename} -> Sanitizado: {result}")
        return result
