"""
Implementación de INameSanitizer para sanitizar nombres de archivos
"""

import re
import os
import logging

from src.core.ports.services.INameSanitizer import INameSanitizer


logger = logging.getLogger(__name__)


class StandardSanitizer(INameSanitizer):
    """
    Sanitizador estándar de nombres de archivos

    Reglas:
    - Extraer año con regex: r'\\(\\d{4}\\)'
    - Reemplazar espacios y guiones bajos por guiones
    - Eliminar caracteres especiales (solo letras, números, guiones y paréntesis)
    - Convertir a minúsculas
    - Siempre terminar en "-optimized.mkv"

    Ejemplos:
    - "Spaceman (2024).mp4" -> "spaceman-(2024)-optimized.mkv"
    - "The Matrix 1999.mkv" -> "the-matrix-(1999)-optimized.mkv"
    - "Inception_2010.avi" -> "inception-(2010)-optimized.mkv"
    """

    def sanitize(self, filename: str) -> str:
        """
        Sanitiza un nombre de archivo para el output

        Args:
            filename: Nombre original del archivo

        Returns:
            Nombre sanitizado para el archivo de salida
        """
        base_name = os.path.splitext(filename)[0]

        year_match = re.search(r"\\(\\d{4}\\)", base_name)
        year = year_match.group(1) if year_match else None

        if year:
            base_name = re.sub(r"\\s*\\(\\d{4}\\)\\s*", "", base_name)

        base_name = base_name.replace(" ", "-").replace("_", "-")

        base_name = re.sub(r"[^a-zA-Z0-9\\-]", "", base_name)

        base_name = base_name.lower()

        base_name = re.sub(r"-+", "-", base_name)

        base_name = base_name.strip("-")

        if year:
            final_name = f"{base_name}-({year})-optimized.mkv"
        else:
            final_name = f"{base_name}-optimized.mkv"

        logger.info(f"[StandardSanitizer] Sanitizado: '{filename}' -> '{final_name}'")
        return final_name
