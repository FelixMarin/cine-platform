"""
Repositorio para el catálogo de cine (omdb_entries y local_content)
Implementación con SQLAlchemy
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from io import BytesIO
import requests

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.infrastructure.models.catalog import OmdbEntry, LocalContent
from src.infrastructure.database.connection import get_db_session


CACHE_EXPIRY_DAYS = 7


class CatalogRepository:
    """Repositorio para el catálogo de cine"""

    def __init__(self, db_session: Session = None):
        self._db = db_session

    def _get_db(self) -> Session:
        if self._db is None:
            self._db = get_db_session()
        return self._db

    def close(self):
        if self._db:
            self._db.close()

    def is_cache_expired(self, entry: OmdbEntry) -> bool:
        """Verifica si la entrada ha expirado"""
        if not entry or not entry.updated_at:
            return True
        expiry_date = entry.updated_at + timedelta(days=CACHE_EXPIRY_DAYS)
        return datetime.utcnow() > expiry_date

    def get_omdb_entry_by_imdb_id(self, imdb_id: str) -> Optional[OmdbEntry]:
        """Obtiene una entrada de OMDB por imdb_id"""
        db = self._get_db()
        return db.query(OmdbEntry).filter(OmdbEntry.imdb_id == imdb_id).first()

    def get_omdb_entry_by_id(self, entry_id: int) -> Optional[OmdbEntry]:
        """Obtiene una entrada de OMDB por ID"""
        db = self._get_db()
        return db.query(OmdbEntry).filter(OmdbEntry.id == entry_id).first()

    def search_omdb_entries(self, query: str, limit: int = 10) -> List[OmdbEntry]:
        """Busca entradas de OMDB por título"""
        db = self._get_db()
        return (
            db.query(OmdbEntry)
            .filter(OmdbEntry.title.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    def create_or_update_omdb_entry(
        self, data: dict, poster_bytes: bytes = None
    ) -> OmdbEntry:
        """Crea o actualiza una entrada de OMDB"""
        db = self._get_db()

        imdb_id = data.get("imdbID")
        if not imdb_id:
            raise ValueError("imdbID es requerido")

        existing = self.get_omdb_entry_by_imdb_id(imdb_id)

        if existing:
            for key, value in data.items():
                if hasattr(existing, key.lower()) and key not in ["id", "created_at"]:
                    setattr(existing, key.lower(), value)
            if poster_bytes:
                existing.poster_image = poster_bytes
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_entry = OmdbEntry.from_omdb_response(data, poster_bytes)
            db.add(new_entry)
            db.commit()
            db.refresh(new_entry)
            return new_entry

    def update_last_accessed(self, entry: OmdbEntry):
        """Actualiza el timestamp de último acceso"""
        db = self._get_db()
        entry.last_accessed = datetime.utcnow()
        db.commit()

    def get_poster_image(self, imdb_id: str) -> Optional[bytes]:
        """Obtiene la imagen del póster"""
        entry = self.get_omdb_entry_by_imdb_id(imdb_id)
        if entry:
            return entry.poster_image
        return None

    def get_local_content_by_id(self, content_id: int) -> Optional[LocalContent]:
        """Obtiene contenido local por ID"""
        db = self._get_db()
        return db.query(LocalContent).filter(LocalContent.id == content_id).first()

    def get_local_content_by_imdb_id(self, imdb_id: str) -> List[LocalContent]:
        """Obtiene contenido local por imdb_id"""
        db = self._get_db()
        return db.query(LocalContent).filter(LocalContent.imdb_id == imdb_id).all()

    def get_local_content_by_file_path(self, file_path: str) -> Optional[LocalContent]:
        """Obtiene contenido local por ruta de archivo"""
        db = self._get_db()
        return (
            db.query(LocalContent).filter(LocalContent.file_path == file_path).first()
        )

    def list_local_content(
        self, content_type: str = None, limit: int = 100, offset: int = 0
    ) -> List[LocalContent]:
        """Lista contenido local"""
        db = self._get_db()
        query = db.query(LocalContent)

        if content_type:
            query = query.filter(LocalContent.type == content_type)

        return query.order_by(LocalContent.title).limit(limit).offset(offset).all()

    def list_movies(self, limit: int = 100, offset: int = 0) -> List[LocalContent]:
        """Lista películas"""
        return self.list_local_content(content_type="movie", limit=limit, offset=offset)

    def list_series(self, limit: int = 100, offset: int = 0) -> List[LocalContent]:
        """Lista series"""
        return self.list_local_content(
            content_type="series", limit=limit, offset=offset
        )

    def create_local_content(self, data: dict) -> LocalContent:
        """Crea contenido local"""
        db = self._get_db()

        content = LocalContent(
            imdb_id=data.get("imdb_id"),
            title=data.get("title"),
            year=data.get("year"),
            rated=data.get("rated"),
            released=data.get("released"),
            runtime=data.get("runtime"),
            genre=data.get("genre"),
            director=data.get("director"),
            writer=data.get("writer"),
            actors=data.get("actors"),
            plot=data.get("plot"),
            language=data.get("language"),
            country=data.get("country"),
            awards=data.get("awards"),
            poster_url=data.get("poster_url"),
            poster_image=data.get("poster_image"),
            metascore=data.get("metascore"),
            imdb_rating=data.get("imdb_rating"),
            imdb_votes=data.get("imdb_votes"),
            type=data.get("type", "movie"),
            box_office=data.get("box_office"),
            production=data.get("production"),
            website=data.get("website"),
            total_seasons=data.get("total_seasons"),
            season=data.get("season"),
            episode=data.get("episode"),
            series_id=data.get("series_id"),
            ratings=data.get("ratings"),
            full_response=data.get("full_response"),
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            duration=data.get("duration"),
            resolution=data.get("resolution"),
            codec=data.get("codec"),
            quality=data.get("quality"),
            format=data.get("format"),
            is_optimized=data.get("is_optimized", False),
            notes=data.get("notes"),
        )

        db.add(content)
        db.commit()
        db.refresh(content)
        return content

    def update_local_content(
        self, content_id: int, data: dict
    ) -> Optional[LocalContent]:
        """Actualiza contenido local"""
        db = self._get_db()

        content = self.get_local_content_by_id(content_id)
        if not content:
            return None

        for key, value in data.items():
            if hasattr(content, key) and key not in ["id", "created_at"]:
                setattr(content, key, value)

        content.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(content)
        return content

    def delete_local_content(self, content_id: int) -> bool:
        """Elimina contenido local"""
        db = self._get_db()

        content = self.get_local_content_by_id(content_id)
        if not content:
            return False

        db.delete(content)
        db.commit()
        return True

    def migrate_local_storage_data(self, data: dict) -> Dict:
        """Migra datos desde localStorage del frontend"""
        db = self._get_db()

        results = {"omdb_entries": 0, "local_content": 0, "errors": []}

        movies_cache = data.get("movies_cache", [])
        series_posts = data.get("series_posts", {})

        for movie_data in movies_cache:
            try:
                imdb_id = movie_data.get("imdb_id") or movie_data.get("imdbID")
                if not imdb_id:
                    results["errors"].append(f"Sin imdb_id: {movie_data.get('title')}")
                    continue

                existing = self.get_omdb_entry_by_imdb_id(imdb_id)
                if not existing:
                    poster_bytes = movie_data.get("poster_image")
                    if isinstance(poster_bytes, str):
                        poster_bytes = (
                            poster_bytes.encode("utf-8")
                            if len(poster_bytes) < 1000000
                            else None
                        )

                    entry = OmdbEntry(
                        imdb_id=imdb_id,
                        title=movie_data.get("title"),
                        year=movie_data.get("year"),
                        type="movie",
                        poster_url=movie_data.get("poster"),
                        poster_image=poster_bytes,
                        full_response=movie_data,
                    )
                    db.add(entry)
                    results["omdb_entries"] += 1

                file_path = movie_data.get("file_path") or movie_data.get("path")
                if file_path:
                    existing_local = self.get_local_content_by_file_path(file_path)
                    if not existing_local:
                        local = LocalContent(
                            imdb_id=imdb_id,
                            title=movie_data.get("title"),
                            year=movie_data.get("year"),
                            type="movie",
                            file_path=file_path,
                            poster_url=movie_data.get("poster"),
                        )
                        db.add(local)
                        results["local_content"] += 1

            except Exception as e:
                results["errors"].append(str(e))

        for series_name, series_data in series_posts.items():
            try:
                imdb_id = series_data.get("imdb_id") or series_data.get("imdbID")

                if imdb_id:
                    existing = self.get_omdb_entry_by_imdb_id(imdb_id)
                    if not existing:
                        poster_bytes = series_data.get("poster_image")
                        if isinstance(poster_bytes, str):
                            poster_bytes = (
                                poster_bytes.encode("utf-8")
                                if len(poster_bytes) < 1000000
                                else None
                            )

                        entry = OmdbEntry(
                            imdb_id=imdb_id,
                            title=series_name,
                            type="series",
                            poster_url=series_data.get("poster"),
                            poster_image=poster_bytes,
                            total_seasons=series_data.get("total_seasons"),
                            full_response=series_data,
                        )
                        db.add(entry)
                        results["omdb_entries"] += 1

                file_path = series_data.get("file_path") or series_data.get("path")
                if file_path:
                    existing_local = self.get_local_content_by_file_path(file_path)
                    if not existing_local:
                        local = LocalContent(
                            imdb_id=imdb_id,
                            title=series_name,
                            type="series",
                            file_path=file_path,
                            poster_url=series_data.get("poster"),
                            season=series_data.get("season"),
                            episode=series_data.get("episode"),
                        )
                        db.add(local)
                        results["local_content"] += 1

            except Exception as e:
                results["errors"].append(str(e))

        db.commit()
        return results


def get_catalog_repository() -> CatalogRepository:
    """Factory para obtener el repositorio"""
    return CatalogRepository()
