"""
Entidad Serie - Representa una serie de TV en el sistema
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class Episode:
    """Entidad que representa un episodio de una serie"""
    
    id: Optional[int] = None
    serie_id: int = 0
    season: int = 1
    episode_number: int = 1
    title: str = ""
    path: str = ""
    filename: str = ""
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # en segundos
    size: Optional[int] = None  # en bytes
    
    # Metadatos de OMDB (opcionales)
    imdb_id: Optional[str] = None
    plot: Optional[str] = None
    aired_date: Optional[str] = None
    
    # Metadatos técnicos
    codec: Optional[str] = None
    resolution: Optional[str] = None
    is_optimized: bool = False
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    @property
    def display_title(self) -> str:
        """Título para mostrar en la UI"""
        return f"T{self.season:02d}E{self.episode_number:02d} - {self.title}"
    
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
            'serie_id': self.serie_id,
            'season': self.season,
            'episode_number': self.episode_number,
            'title': self.title,
            'display_title': self.display_title,
            'path': self.path,
            'filename': self.filename,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'size': self.size,
            'size_mb': self.size_mb,
            'imdb_id': self.imdb_id,
            'plot': self.plot,
            'aired_date': self.aired_date,
            'codec': self.codec,
            'resolution': self.resolution,
            'is_optimized': self.is_optimized,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Episode':
        """Crea una entidad desde un diccionario"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Serie:
    """Entidad que representa una serie de TV"""
    
    id: Optional[int] = None
    name: str = ""
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    path: str = ""
    thumbnail: Optional[str] = None
    
    # Metadatos de OMDB (opcionales)
    imdb_id: Optional[str] = None
    plot: Optional[str] = None
    genre: Optional[str] = None
    creator: Optional[str] = None
    actors: Optional[str] = None
    poster: Optional[str] = None
    imdb_rating: Optional[float] = None
    total_seasons: Optional[int] = None
    runtime: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    awards: Optional[str] = None
    
    # Relaciones
    episodes: List[Episode] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    @property
    def display_title(self) -> str:
        """Título para mostrar en la UI"""
        if self.year_start:
            if self.year_end and self.year_end != self.year_start:
                return f"{self.name} ({self.year_start}-{self.year_end})"
            return f"{self.name} ({self.year_start})"
        return self.name
    
    @property
    def total_episodes(self) -> int:
        """Número total de episodios"""
        return len(self.episodes)
    
    @property
    def seasons(self) -> List[int]:
        """Lista de temporadas disponibles"""
        return sorted(list(set(ep.season for ep in self.episodes)))
    
    def get_episodes_by_season(self, season: int) -> List[Episode]:
        """Obtiene los episodios de una temporada específica"""
        return sorted(
            [ep for ep in self.episodes if ep.season == season],
            key=lambda e: e.episode_number
        )
    
    def to_dict(self) -> Dict:
        """Convierte la entidad a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'display_title': self.display_title,
            'year_start': self.year_start,
            'year_end': self.year_end,
            'path': self.path,
            'thumbnail': self.thumbnail,
            'imdb_id': self.imdb_id,
            'plot': self.plot,
            'genre': self.genre,
            'creator': self.creator,
            'actors': self.actors,
            'poster': self.poster,
            'imdb_rating': self.imdb_rating,
            'total_seasons': self.total_seasons,
            'total_episodes': self.total_episodes,
            'seasons': self.seasons,
            'runtime': self.runtime,
            'language': self.language,
            'country': self.country,
            'awards': self.awards,
            'episodes': [ep.to_dict() for ep in self.episodes],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Serie':
        """Crea una entidad desde un diccionario"""
        episodes_data = data.pop('episodes', [])
        serie = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        serie.episodes = [Episode.from_dict(ep) for ep in episodes_data]
        return serie
