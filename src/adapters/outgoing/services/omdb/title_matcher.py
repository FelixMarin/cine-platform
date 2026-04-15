"""
Servicio de matching de títulos OMDB

Maneja la lógica de comparación de títulos y años entre búsquedas y resultados de OMDB.
"""

import logging
import re

logger = logging.getLogger(__name__)


class OMDBTitleMatcher:
    """Lógica de matching de títulos y años para OMDB"""

    @staticmethod
    def clean_title_and_year(raw_title: str) -> tuple:
        """
        Extrae título limpio y año del string.
        Ejemplo: "F1 the movie (2025)" -> ("F1 the movie", 2025)
        """
        year_match = re.search(r"\((\d{4})\)\s*$", raw_title)
        if year_match:
            year = int(year_match.group(1))
            clean_title = re.sub(r"\s*\(\d{4}\)\s*$", "", raw_title).strip()
            return clean_title, year
        return raw_title.strip(), None

    @staticmethod
    def is_exact_match(
        search_title: str, search_year: str, result_title: str, result_year: str
    ) -> bool:
        """
        Verifica si el resultado de OMDB coincide con lo buscado.
        """
        if not result_title:
            return False

        if not OMDBTitleMatcher._years_match(search_year, result_year):
            logger.info(f"OMDB: Año no coincide: '{search_year}' vs '{result_year}'")
            return False

        if not OMDBTitleMatcher._titles_match_semantically(search_title, result_title):
            logger.info(
                f"OMDB: Título no coincide semánticamente: '{search_title}' vs '{result_title}'"
            )
            return False

        return True

    @staticmethod
    def _years_match(search_year: str, result_year: str) -> bool:
        """Verifica si los años coinciden"""
        if not search_year or not result_year:
            return False
        return search_year == result_year

    @staticmethod
    def _titles_match_semantically(search_title: str, result_title: str) -> bool:
        """Verifica coincidencia semántica de títulos"""
        if not search_title or not result_title:
            return False

        s_clean = search_title.lower().strip()
        r_clean = result_title.lower().strip()

        if s_clean == r_clean:
            return True

        s_words = set(re.findall(r"\w+", s_clean))
        r_words = set(re.findall(r"\w+", r_clean))

        common = s_words & r_words
        if not common:
            return False

        min_len = min(len(s_words), len(r_words))
        similarity = len(common) / min_len

        return similarity >= 0.7
