"""
Entidad Movie - Representa una película en el sistema
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class Movie:
    """Entidad que representa una película en el catálogo"""
    
    id: Optional[int] = None
    title: str = ""
    year: Optional[int] = None
    path: str = ""
    filename: str = ""
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # en segundos
    size: Optional[int] = None  # en bytes
    
    # Metadatos de OMDB (opcionales)
    imdb_id: Optional[str] = None
    plot: Optional[str] = None
    genre: Optional[str] = None
    director: Optional[str] = None
    actors: Optional[str] = None
    poster: Optional[str] = None
    imdb_rating: Optional[float] = None
    runtime: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    awards: Optional[str] = None
    box_office: Optional[str] = None
    production: Optional[str] = None
    
    # Metadatos técnicos
    codec: Optional[str] = None
    resolution: Optional[str] = None
    is_optimized: bool = False
    optimized_profile: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Relaciones
    metadata_source: str = "local"  # 'omdb', 'local', 'tmdb'
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    @property
    def title_clean(self) -> str:
        """Título limpio sin año ni sufijos"""
        import re
        title = self.title
        # Quitar año entre paréntesis
        title = re.sub(r'\s*\(\d{4}\)\s*', '', title)
        # Quitar sufijo -optimized
        title = title.replace('-optimized', '').strip()
        return title
    
    @property
    def display_title(self) -> str:
        """Título para mostrar en la UI"""
        if self.year:
            return f"{self.title_clean} ({self.year})"
        return self.title_clean
    
    @property
    def size_mb(self) -> Optional[float]:
        """Tamaño en MB"""
        if self.size:
            return self.size / (1024 * 1024)
        return None
    
    @property
    def duration_formatted(self) -> Optional[str]:
        """Duración formateada como HH:MM:SS"""
        if self.duration:
            hours = self.duration // 3600
            minutes = (self.duration % 3600) // 60
            seconds = self.duration % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None
    
    def to_dict(self) -> Dict:
        """Convierte la entidad a diccionario"""
        return {
            'id': self.id,
            'title': self.title,
            'title_clean': self.title_clean,
            'display_title': self.display_title,
            'year': self.year,
            'path': self.path,
            'filename': self.filename,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'size': self.size,
            'size_mb': self.size_mb,
            'imdb_id': self.imdb_id,
            'plot': self.plot,
            'genre': self.genre,
            'director': self.director,
            'actors': self.actors,
            'poster': self.poster,
            'imdb_rating': self.imdb_rating,
            'runtime': self.runtime,
            'language': self.language,
            'country': self.country,
            'awards': self.awards,
            'box_office': self.box_office,
            'production': self.production,
            'codec': self.codec,
            'resolution': self.resolution,
            'is_optimized': self.is_optimized,
            'optimized_profile': self.optimized_profile,
            'metadata_source': self.metadata_source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Movie':
        """Crea una entidad desde un diccionario"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
