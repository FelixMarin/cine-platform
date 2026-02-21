"""
Entidad Progress - Representa el progreso de reproducción de un usuario
"""
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class MediaType(Enum):
    """Tipo de contenido multimedia"""
    MOVIE = "movie"
    EPISODE = "episode"


@dataclass
class Progress:
    """Entidad que representa el progreso de reproducción"""
    
    id: Optional[int] = None
    user_id: int = 0
    media_type: MediaType = MediaType.MOVIE
    media_id: int = 0  # movie_id o episode_id
    
    # Posición en segundos
    position: int = 0
    duration: int = 0  # duración total en segundos
    
    # Estado
    is_completed: bool = False
    watch_count: int = 0  # veces que ha sido reproducido
    
    # Timestamps
    last_watched: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_watched is None:
            self.last_watched = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if isinstance(self.media_type, str):
            self.media_type = MediaType(self.media_type)
    
    @property
    def percentage(self) -> float:
        """Porcentaje de reproducción completado"""
        if self.duration > 0:
            return min((self.position / self.duration) * 100, 100)
        return 0
    
    @property
    def position_formatted(self) -> str:
        """Posición formateada como HH:MM:SS"""
        hours = self.position // 3600
        minutes = (self.position % 3600) // 60
        seconds = self.position % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @property
    def duration_formatted(self) -> str:
        """Duración formateada como HH:MM:SS"""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @property
    def remaining_time(self) -> int:
        """Tiempo restante en segundos"""
        return max(self.duration - self.position, 0)
    
    @property
    def remaining_formatted(self) -> str:
        """Tiempo restante formateado"""
        remaining = self.remaining_time
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def update_position(self, new_position: int):
        """Actualiza la posición de reproducción"""
        self.position = new_position
        self.last_watched = datetime.now()
        self.updated_at = datetime.now()
        
        # Marcar como completado si se ha visto más del 90%
        if self.duration > 0 and self.position >= self.duration * 0.9:
            self.is_completed = True
    
    def mark_completed(self):
        """Marca el contenido como completado"""
        self.is_completed = True
        self.position = self.duration
        self.updated_at = datetime.now()
    
    def increment_watch_count(self):
        """Incrementa el contador de reproducciones"""
        self.watch_count += 1
        self.last_watched = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convierte la entidad a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'media_type': self.media_type.value if isinstance(self.media_type, MediaType) else self.media_type,
            'media_id': self.media_id,
            'position': self.position,
            'position_formatted': self.position_formatted,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'percentage': self.percentage,
            'is_completed': self.is_completed,
            'watch_count': self.watch_count,
            'remaining_time': self.remaining_time,
            'remaining_formatted': self.remaining_formatted,
            'last_watched': self.last_watched.isoformat() if self.last_watched else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Progress':
        """Crea una entidad desde un diccionario"""
        if 'media_type' in data and isinstance(data['media_type'], str):
            data['media_type'] = MediaType(data['media_type'])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
