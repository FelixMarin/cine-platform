"""
Modelo SQLAlchemy para el historial de optimizaciones
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    BigInteger,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func
from src.infrastructure.models.catalog import Base


class OptimizationHistory(Base):
    """Modelo para el historial de optimizaciones de torrents"""

    __tablename__ = "optimization_history"

    id = Column(Integer, primary_key=True)
    process_id = Column(String(36), unique=True, nullable=False, index=True)
    torrent_id = Column(Integer, nullable=True)
    torrent_name = Column(String(500), nullable=False)
    movie_name = Column(String(255), nullable=False)  # Este campo existe en la tabla
    category = Column(String(100), nullable=False)

    # Archivos - coinciden con la tabla
    input_file = Column(String(500), nullable=True)
    output_file = Column(String(500), nullable=True)
    output_filename = Column(String(500), nullable=True)

    # Fechas - USAR LOS NOMBRES CORRECTOS DE LA TABLA
    download_started = Column("torrent_download_start", DateTime, nullable=True)
    download_completed = Column("torrent_download_end", DateTime, nullable=True)
    optimization_started = Column("optimization_started", DateTime, nullable=True)
    optimization_completed = Column("optimization_completed", DateTime, nullable=True)

    # Resultado
    status = Column(
        String(20), nullable=False, index=True
    )  # 'completed', 'error', 'cancelled'
    error_message = Column(Text, nullable=True)

    # Tamaños y compresión - USAR NOMBRES CORRECTOS
    optimized_size_bytes = Column("file_size_bytes", BigInteger, nullable=True)
    original_size_bytes = Column(BigInteger, nullable=True)
    compression_ratio = Column(Numeric(5, 2), nullable=True)

    # Tracking
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # app_user_id es NOT NULL en la tabla
    app_user_id = Column(Integer, nullable=False)

    # Propiedades calculadas (no son columnas, se calculan al vuelo)
    @property
    def torrent_download_start(self):
        return self.download_started

    @property
    def torrent_download_end(self):
        return self.download_completed

    @property
    def optimization_start(self):
        return self.optimization_started

    @property
    def optimization_end(self):
        return self.optimization_completed

    @property
    def file_size_bytes(self):
        return self.optimized_size_bytes

    @property
    def download_duration_seconds(self):
        """Calcula duración de descarga en segundos"""
        if self.download_started and self.download_completed:
            delta = self.download_completed - self.download_started
            return int(delta.total_seconds())
        return None

    @property
    def optimization_duration_seconds(self):
        """Calcula duración de optimización en segundos"""
        if self.optimization_started and self.optimization_completed:
            delta = self.optimization_completed - self.optimization_started
            return int(delta.total_seconds())
        return None

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "process_id": self.process_id,
            "torrent_id": self.torrent_id,
            "torrent_name": self.torrent_name,
            "movie_name": self.movie_name,
            "category": self.category,
            "input_file": self.input_file,
            "output_file": self.output_file,
            "output_filename": self.output_filename,
            # Usar las propiedades para mantener compatibilidad
            "torrent_download_start": self.torrent_download_start.isoformat()
            if self.torrent_download_start
            else None,
            "torrent_download_end": self.torrent_download_end.isoformat()
            if self.torrent_download_end
            else None,
            "optimization_start": self.optimization_start.isoformat()
            if self.optimization_start
            else None,
            "optimization_end": self.optimization_end.isoformat()
            if self.optimization_end
            else None,
            "download_duration_seconds": self.download_duration_seconds,
            "optimization_duration_seconds": self.optimization_duration_seconds,
            "status": self.status,
            "error_message": self.error_message,
            "file_size_bytes": self.file_size_bytes,
            "original_size_bytes": self.original_size_bytes,
            "compression_ratio": float(self.compression_ratio)
            if self.compression_ratio
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
