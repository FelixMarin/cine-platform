"""
Modelos SQLAlchemy para el catálogo de cine
Tablas: omdb_entries, local_content
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    Boolean,
    DateTime,
    BigInteger,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB, BYTEA
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import logging

Base = declarative_base()
logger = logging.getLogger(__name__)


class OmdbEntry(Base):
    """Modelo para entradas de OMDB"""

    __tablename__ = "omdb_entries"

    id = Column(Integer, primary_key=True)
    imdb_id = Column(String(20), unique=True, nullable=True, index=True)
    title = Column(String(500), nullable=True)
    year = Column(String(10))
    rated = Column(String(10))
    released = Column(String(50))
    runtime = Column(String(50))
    genre = Column(String(500))
    director = Column(String(500))
    writer = Column(String(1000))
    actors = Column(String(2000))
    plot = Column(Text)
    language = Column(String(500))
    country = Column(String(200))
    awards = Column(String(500))
    poster_url = Column(String(1000))
    poster_image = Column(BYTEA)
    metascore = Column(Integer)
    imdb_rating = Column(Numeric(3, 1))
    imdb_votes = Column(String(20))
    type = Column(String(20), index=True)
    box_office = Column(String(50))
    production = Column(String(500))
    website = Column(String(500))
    dvd_release = Column(String(50))
    total_seasons = Column(Integer)
    season = Column(Integer)
    episode = Column(Integer)
    series_id = Column(String(20))
    ratings = Column(JSONB)
    full_response = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime)

    local_contents = relationship(
        "LocalContent",
        back_populates="omdb_entry",
        foreign_keys="LocalContent.imdb_id",
    )

    def to_dict(self, include_image=False):
        """Convierte el modelo a diccionario de forma segura"""
        try:
            result = {
                "id": self.id,
                "imdb_id": self.imdb_id,
                "title": self.title,
                "year": self.year,
                "rated": self.rated,
                "released": self.released,
                "runtime": self.runtime,
                "genre": self.genre,
                "director": self.director,
                "writer": self.writer,
                "actors": self.actors,
                "plot": self.plot,
                "language": self.language,
                "country": self.country,
                "awards": self.awards,
                "poster_url": self.poster_url,
                "metascore": self.metascore,
                "imdb_rating": float(self.imdb_rating) if self.imdb_rating else None,
                "imdb_votes": self.imdb_votes,
                "type": self.type,
                "box_office": self.box_office,
                "production": self.production,
                "website": self.website,
                "dvd_release": self.dvd_release,
                "total_seasons": self.total_seasons,
                "season": self.season,
                "episode": self.episode,
                "series_id": self.series_id,
                "ratings": self.ratings,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
            if include_image and self.poster_image:
                result["has_poster_image"] = True
            return result
        except Exception as e:
            logger.error(f"Error en OmdbEntry.to_dict: {e}")
            return {"id": self.id, "error": "Error al serializar"}

    @classmethod
    def from_omdb_response(cls, data: dict, poster_bytes: bytes = None):
        """Crea una instancia desde la respuesta de OMDB"""
        
        def safe_int(value, default=None):
            """Convierte un valor a entero de forma segura, manejando 'N/A' y otros valores"""
            if value is None or value == '' or value == 'N/A':
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        def safe_float(value, default=None):
            """Convierte un valor a float de forma segura, manejando 'N/A' y otros valores"""
            if value is None or value == '' or value == 'N/A':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        return cls(
            imdb_id=data.get("imdbID"),
            title=data.get("Title"),
            year=data.get("Year"),
            rated=data.get("Rated"),
            released=data.get("Released"),
            runtime=data.get("Runtime"),
            genre=data.get("Genre"),
            director=data.get("Director"),
            writer=data.get("Writer"),
            actors=data.get("Actors"),
            plot=data.get("Plot"),
            language=data.get("Language"),
            country=data.get("Country"),
            awards=data.get("Awards"),
            poster_url=data.get("Poster"),
            poster_image=poster_bytes,
            metascore=safe_int(data.get("Metascore")),
            imdb_rating=safe_float(data.get("imdbRating")),
            imdb_votes=data.get("imdbVotes"),
            type=data.get("Type"),
            box_office=data.get("BoxOffice"),
            production=data.get("Production"),
            website=data.get("Website"),
            total_seasons=safe_int(data.get("totalSeasons")),
            ratings=data.get("Ratings"),
            full_response=data,
        )


class LocalContent(Base):
    """Modelo para contenido local (archivos de películas/series)"""

    __tablename__ = "local_content"

    id = Column(Integer, primary_key=True)
    imdb_id = Column(
        String(20), ForeignKey("omdb_entries.imdb_id"), nullable=True, index=True
    )
    title = Column(String(500))
    year = Column(String(10))
    rated = Column(String(10))
    released = Column(String(50))
    runtime = Column(String(50))
    genre = Column(String(500))
    director = Column(String(500))
    writer = Column(String(1000))
    actors = Column(String(2000))
    plot = Column(Text)
    language = Column(String(500))
    country = Column(String(200))
    awards = Column(String(500))
    poster_url = Column(String(1000))
    poster_image = Column(BYTEA)
    metascore = Column(Integer)
    imdb_rating = Column(Numeric(3, 1))
    imdb_votes = Column(String(20))
    type = Column(String(20), index=True)
    box_office = Column(String(50))
    production = Column(String(500))
    website = Column(String(500))
    dvd_release = Column(String(50))
    total_seasons = Column(Integer)
    season = Column(Integer)
    episode = Column(Integer)
    series_id = Column(String(20))
    ratings = Column(JSONB)
    full_response = Column(JSONB)
    file_path = Column(String(1000), nullable=True)
    file_size = Column(BigInteger)
    duration = Column(String(20))
    resolution = Column(String(20))
    codec = Column(String(50))
    quality = Column(String(50))
    format = Column(String(20))
    is_optimized = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    omdb_entry = relationship(
        "OmdbEntry", back_populates="local_contents", foreign_keys=[imdb_id]
    )

    def to_dict(self, include_image=False):
        """Convierte el modelo a diccionario de forma segura"""
        try:
            result = {
                "id": self.id,
                "imdb_id": self.imdb_id,
                "title": self.title,
                "year": self.year,
                "rated": self.rated,
                "released": self.released,
                "runtime": self.runtime,
                "genre": self.genre,
                "director": self.director,
                "writer": self.writer,
                "actors": self.actors,
                "plot": self.plot,
                "language": self.language,
                "country": self.country,
                "awards": self.awards,
                "poster_url": self.poster_url,
                "metascore": self.metascore,
                "imdb_rating": float(self.imdb_rating) if self.imdb_rating else None,
                "imdb_votes": self.imdb_votes,
                "type": self.type,
                "box_office": self.box_office,
                "production": self.production,
                "website": self.website,
                "dvd_release": self.dvd_release,
                "total_seasons": self.total_seasons,
                "season": self.season,
                "episode": self.episode,
                "series_id": self.series_id,
                "ratings": self.ratings,
                "file_path": self.file_path,
                "file_size": self.file_size,
                "duration": self.duration,
                "resolution": self.resolution,
                "codec": self.codec,
                "quality": self.quality,
                "format": self.format,
                "is_optimized": self.is_optimized,
                "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
            if include_image and self.poster_image:
                result["has_poster_image"] = True
            return result
        except Exception as e:
            logger.error(f"Error en LocalContent.to_dict: {e}")
            return {"id": self.id, "error": "Error al serializar"}
