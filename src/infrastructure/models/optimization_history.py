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
    category = Column(String(100), nullable=False)
    input_file = Column(String(500), nullable=True)
    output_file = Column(String(500), nullable=True)
    output_filename = Column(String(500), nullable=True)

    # Fechas y duraciones
    torrent_download_start = Column(DateTime, nullable=True)
    torrent_download_end = Column(DateTime, nullable=True)
    optimization_start = Column(DateTime, nullable=False)
    optimization_end = Column(DateTime, nullable=True)

    # Duración en segundos
    download_duration_seconds = Column(Integer, nullable=True)
    optimization_duration_seconds = Column(Integer, nullable=True)

    # Resultado
    status = Column(String(20), nullable=False, index=True)  # 'completed', 'error', 'cancelled'
    error_message = Column(Text, nullable=True)

    # Tamaños y compresión
    file_size_bytes = Column(BigInteger, nullable=True)
    original_size_bytes = Column(BigInteger, nullable=True)
    compression_ratio = Column(Numeric(5, 2), nullable=True)

    # Tracking
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Nota: app_user_id se guarda como integer simple ya que la tabla app_users
    # no existe como modelo SQLAlchemy. Si en el futuro se crea la tabla,
    # se puede agregar la ForeignKey.
    app_user_id = Column(Integer, nullable=True)

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "process_id": self.process_id,
            "torrent_id": self.torrent_id,
            "torrent_name": self.torrent_name,
            "category": self.category,
            "input_file": self.input_file,
            "output_file": self.output_file,
            "output_filename": self.output_filename,
            "torrent_download_start": self.torrent_download_start.isoformat() if self.torrent_download_start else None,
            "torrent_download_end": self.torrent_download_end.isoformat() if self.torrent_download_end else None,
            "optimization_start": self.optimization_start.isoformat() if self.optimization_start else None,
            "optimization_end": self.optimization_end.isoformat() if self.optimization_end else None,
            "download_duration_seconds": self.download_duration_seconds,
            "optimization_duration_seconds": self.optimization_duration_seconds,
            "status": self.status,
            "error_message": self.error_message,
            "file_size_bytes": self.file_size_bytes,
            "original_size_bytes": self.original_size_bytes,
            "compression_ratio": float(self.compression_ratio) if self.compression_ratio else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
