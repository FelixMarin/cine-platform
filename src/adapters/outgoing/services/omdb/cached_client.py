"""
Servicio de metadatos OMDB con caché en base de datos
Extiende el cliente OMDB básico con caché en PostgreSQL
"""

import io
import os
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from src.adapters.outgoing.services.omdb.client import OMDBMetadataService
from src.adapters.outgoing.repositories.postgresql.catalog_repository import (
    CatalogRepository,
    get_catalog_repository,
    get_catalog_repository_session,
)


CACHE_EXPIRY_DAYS = 7


class OMDBMetadataServiceCached(OMDBMetadataService):
    """Servicio de metadatos OMDB con caché en PostgreSQL"""

    def __init__(self, api_key: str = None, language: str = "es"):
        super().__init__(api_key, language)
        # Ya no guardamos el repo como atributo - cada operación usa su propia sesión

    # Este método ya no se necesita - los métodos usan get_catalog_repository_session() directamente

    def _download_poster(self, poster_url: str) -> Optional[bytes]:
        """Descarga la imagen del póster"""
        if not poster_url or poster_url == "N/A":
            return None

        try:
            response = requests.get(poster_url, timeout=10)
            if response.status_code == 200 and len(response.content) < 5_000_000:
                return response.content
        except Exception:
            pass
        return None

    def _is_cache_expired(self, entry) -> bool:
        """Verifica si la entrada ha expirado"""
        if not entry or not entry.updated_at:
            return True
        expiry_date = entry.updated_at + timedelta(days=CACHE_EXPIRY_DAYS)
        return datetime.utcnow() > expiry_date

    def get_movie_by_imdb_id(
        self, imdb_id: str, force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Obtiene metadatos de una película por IMDB ID con caché

        Args:
            imdb_id: ID de IMDb (ej: tt1234567)
            force_refresh: Si True, fuerza actualización desde OMDB

        Returns:
            Diccionario con metadatos o None
        """
        # Usar context manager para garantizar cierre de sesión
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            
            existing = repo.get_omdb_entry_by_imdb_id(imdb_id)

            if existing and not force_refresh:
                if not self._is_cache_expired(existing):
                    repo.update_last_accessed(existing)
                    return existing.to_dict(include_image=True)

            omdb_data = self._make_request({"i": imdb_id, "plot": "full", "r": "json"})

            if not omdb_data or omdb_data.get("Response") == "False":
                if existing:
                    return existing.to_dict(include_image=True)
                return None

            poster_bytes = None
            poster_url = omdb_data.get("Poster")
            if poster_url and poster_url != "N/A":
                poster_bytes = self._download_poster(poster_url)

            entry = repo.create_or_update_omdb_entry(omdb_data, poster_bytes)

            return entry.to_dict(include_image=True)

    def search_movies_cached(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Busca películas con caché

        Primero busca en la BBDD local, luego en OMDB si no hay suficientes resultados
        """
        # Usar context manager para garantizar cierre de sesión
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)

            local_results = repo.search_omdb_entries(query, limit=limit)

            if len(local_results) >= limit:
                return [r.to_dict() for r in local_results]

            omdb_results = self.search_movies(query)

            for result in omdb_results:
                imdb_id = result.get("imdbID")
                if imdb_id:
                    existing = repo.get_omdb_entry_by_imdb_id(imdb_id)
                    if not existing:
                        try:
                            # Hacer la búsqueda internamente para no abrir otra sesión
                            self.get_movie_by_imdb_id(imdb_id)
                        except Exception:
                            pass

            all_results = repo.search_omdb_entries(query, limit=limit)
            return [r.to_dict() for r in all_results]

    def get_serie_by_imdb_id(
        self, imdb_id: str, force_refresh: bool = False
    ) -> Optional[Dict]:
        """Obtiene metadatos de una serie por IMDB ID"""
        return self.get_movie_by_imdb_id(imdb_id, force_refresh)

    def get_poster_image(self, imdb_id: str) -> Optional[bytes]:
        """Obtiene la imagen del póster desde la BBDD"""
        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            return repo.get_poster_image(imdb_id)

    def save_poster_for_content(self, imdb_id: str, content_id: int) -> bool:
        """Guarda el póster de OMDB para contenido local"""
        movie_data = self.get_movie_by_imdb_id(imdb_id)

        if not movie_data:
            return False

        with get_catalog_repository_session() as db:
            repo = get_catalog_repository(db)
            poster_bytes = repo.get_poster_image(imdb_id)

            if poster_bytes:
                content = repo.get_local_content_by_id(content_id)
                if content:
                    content.poster_image = poster_bytes
                    db.commit()
                    return True

        return False


def get_omdb_service_cached() -> OMDBMetadataServiceCached:
    """Factory para obtener el servicio OMDB con caché"""
    return OMDBMetadataServiceCached()
