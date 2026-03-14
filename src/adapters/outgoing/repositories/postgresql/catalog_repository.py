"""
Repositorio para el catálogo de cine (omdb_entries y local_content)
Implementación con SQLAlchemy

PATRÓN: Cada operación crea su propia sesión - NO usa singleton
Usa context manager para garantizar cierre de sesiones
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from io import BytesIO
import logging
import re
from contextlib import contextmanager

import requests

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.infrastructure.models.catalog import OmdbEntry, LocalContent
from src.infrastructure.database.connection import get_session_maker


logger = logging.getLogger(__name__)
CACHE_EXPIRY_DAYS = 7


@contextmanager
def get_catalog_repository_session():
    """
    Context manager para obtener una sesión de base de datos.
    Garantiza que la sesión se cierre correctamente.
    """
    SessionMaker = get_session_maker()
    session = SessionMaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CatalogRepository:
    """
    Repositorio para el catálogo de cine.
    
    IMPORTANTE: Ahora acepta una sesión en el constructor.
    Para usar correctamente, emplea get_catalog_repository_session() como context manager.
    """

    def __init__(self, db_session: Session = None):
        self._db = db_session
        self._owns_session = db_session is None
        self._session_maker = None

    def _get_db(self) -> Session:
        if self._db is None:
            # Crear nueva sesión para esta operación
            SessionMaker = get_session_maker()
            self._db = SessionMaker()
            self._owns_session = True
        return self._db

    def close(self):
        """Cierra la sesión de base de datos si es-owned"""
        if self._db and self._owns_session:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None
            self._owns_session = False

    def rollback(self):
        """Hace rollback de la transacción actual"""
        if self._db:
            self._db.rollback()

    def __enter__(self):
        """Soporte para context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión al salir del context manager"""
        self.close()
        return False

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
        """Busca entradas de OMDB por título (búsqueda parcial - ILIKE)"""
        db = self._get_db()
        return (
            db.query(OmdbEntry)
            .filter(OmdbEntry.title.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    def get_exact_match(self, title: str, year: Optional[int]) -> Optional[OmdbEntry]:
        """
        Busca una entrada que coincida EXACTAMENTE con el título y año (como OMDB).
        
        Args:
            title: Título exacto (sin comodines)
            year: Año exacto (opcional)
        
        Returns:
            OmdbEntry o None
        """
        db = self._get_db()
        query = db.query(OmdbEntry).filter(
            func.lower(OmdbEntry.title) == func.lower(title.strip())
        )
        
        if year:
            query = query.filter(OmdbEntry.year == str(year))
        
        return query.first()

    def get_exact_match_by_cleaned_title(self, raw_title: str, year: Optional[int]) -> Optional[OmdbEntry]:
        """
        Extrae el título limpio (sin años entre paréntesis) y busca coincidencia exacta.
        
        Args:
            raw_title: Título que puede incluir (2025) al final
            year: Año opcional
        
        Returns:
            OmdbEntry o None
        """
        # Extraer año del título si está entre paréntesis
        year_match = re.search(r'\((\d{4})\)', raw_title)
        if year_match and not year:
            year = int(year_match.group(1))
        
        # Limpiar título: quitar (año) y limpiar espacios
        clean_title = re.sub(r'\s*\(\d{4}\)\s*$', '', raw_title).strip()
        
        return self.get_exact_match(clean_title, year)

    # ELIMINADO: Búsqueda de fallback con ILIKE que causaba thumbnails incorrectos
    # Este método ya no se usa - el servicio de thumbnails ahora solo usa búsqueda exacta
    # def search_omdb_entries_fallback(self, title: str, limit: int = 10) -> List[OmdbEntry]:
    #     """
    #     BÚSQUEDA DE FALLBACK: solo usar ILIKE cuando no hay coincidencia exacta.
    #     Útil para depuración y para encontrar entradas cuando no hay coincidencia exacta.
    #     
    #     Args:
    #         title: Título a buscar
    #         limit: Límite de resultados
    #     
    #     Returns:
    #         Lista de OmdbEntry que coinciden parcialmente
    #     """
    #     logger.warning(f"⚠️ Usando búsqueda fallback ILIKE para: {title}")
    #     db = self._get_db()
    #     return (
    #         db.query(OmdbEntry)
    #         .filter(OmdbEntry.title.ilike(f"%{title}%"))
    #         .limit(limit)
    #         .all()
    #     )

    def create_or_update_omdb_entry(
        self, data: dict, poster_bytes: bytes = None
    ) -> OmdbEntry:
        """Crea o actualiza una entrada de OMDB"""
        db = self._get_db()
        
        # Campos que deben ser convertidos a entero
        integer_fields = {'metascore', 'totalseasons'}
        # Campos que deben ser convertidos a float
        float_fields = {'imdbrating'}

        def convert_value(key, value):
            """Convierte valores de OMDB handles 'N/A' correctly"""
            if value is None or value == '' or value == 'N/A':
                return None
            key_lower = key.lower()
            if key_lower in integer_fields:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            elif key_lower in float_fields:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            return value

        try:
            imdb_id = data.get("imdbID")
            if not imdb_id:
                raise ValueError("imdbID es requerido")

            existing = self.get_omdb_entry_by_imdb_id(imdb_id)

            if existing:
                for key, value in data.items():
                    if hasattr(existing, key.lower()) and key not in ["id", "created_at"]:
                        # Convertir valores para campos numéricos
                        converted_value = convert_value(key, value)
                        setattr(existing, key.lower(), converted_value)
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
        except Exception as e:
            db.rollback()
            logger.error(f"Error en create_or_update_omdb_entry: {e}")
            raise

    def update_last_accessed(self, entry: OmdbEntry):
        """Actualiza el timestamp de último acceso"""
        db = self._get_db()
        try:
            entry.last_accessed = datetime.utcnow()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error en update_last_accessed: {e}")
            raise

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

        try:
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
        except Exception as e:
            db.rollback()
            logger.error(f"Error en create_local_content: {e}")
            raise

    def update_local_content(
        self, content_id: int, data: dict
    ) -> Optional[LocalContent]:
        """Actualiza contenido local"""
        db = self._get_db()

        try:
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
        except Exception as e:
            db.rollback()
            logger.error(f"Error en update_local_content: {e}")
            raise

    def delete_local_content(self, content_id: int) -> bool:
        """Elimina contenido local"""
        db = self._get_db()

        try:
            content = self.get_local_content_by_id(content_id)
            if not content:
                return False

            db.delete(content)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error en delete_local_content: {e}")
            raise

    def migrate_local_storage_data(self, data: dict) -> Dict:
        """Migra datos desde localStorage del frontend"""
        db = self._get_db()

        results = {"omdb_entries": 0, "local_content": 0, "errors": []}

        try:
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
        except Exception as e:
            db.rollback()
            logger.error(f"Error en migrate_local_storage_data: {e}")
            raise


@contextmanager
def get_catalog_repository_session():
    """
    Context manager para obtener una sesión de base de datos.
    Garantiza que la sesión se cierre correctamente.
    
    Uso:
    ```python
    with get_catalog_repository_session() as db:
        repo = CatalogRepository(db)
        entry = repo.get_exact_match(title, year)
    # Sesión se cierra automáticamente
    ```
    """
    SessionMaker = get_session_maker()
    session = SessionMaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_catalog_repository(db_session: Session = None) -> CatalogRepository:
    """
    Factory para obtener el repositorio.
    
    Args:
        db_session: Sesión existente (opcional). Si no se provee, 
                   el repositorio creará su propia sesión.
    
    Returns:
        CatalogRepository: Instancia del repositorio
    
    Uso recomendado con context manager:
    ```python
    with get_catalog_repository() as repo:
        entry = repo.get_exact_match(title, year)
    # Sesión se cierra automáticamente
    ```
    """
    return CatalogRepository(db_session)
