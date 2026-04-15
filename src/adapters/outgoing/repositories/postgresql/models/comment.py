"""
Modelos SQLAlchemy para comentarios de películas
Tablas: movie_comments, movie_comment_likes, movie_comment_reports
"""

import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()
logger = logging.getLogger(__name__)


class MovieComment(Base):
    """Modelo para comentarios de películas"""

    __tablename__ = "movie_comments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True, name='app_user_id')
    movie_id = Column(Integer, nullable=False, index=True)
    movie_title = Column(String(500), nullable=False)
    tmdb_id = Column(Integer, nullable=True, index=True)
    comment_text = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, nullable=True, index=True)
    is_spoiler = Column(Boolean, default=False, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    is_reported = Column(Boolean, default=False, nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)
    hidden_reason = Column(String(500), nullable=True)
    likes_count = Column(Integer, default=0, nullable=False)
    replies_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    likes = relationship("MovieCommentLike", back_populates="comment", cascade="all, delete-orphan")
    reports = relationship("MovieCommentReport", back_populates="comment", cascade="all, delete-orphan")

    # Comentario padre (para respuestas)
    parent_comment = relationship("MovieComment", remote_side=[id], backref="replies")

    def to_dict(self, include_relations=False):
        """Convierte el modelo a diccionario"""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'movie_title': self.movie_title,
            'tmdb_id': self.tmdb_id,
            'comment_text': self.comment_text,
            'parent_comment_id': self.parent_comment_id,
            'is_spoiler': self.is_spoiler,
            'is_edited': self.is_edited,
            'is_reported': self.is_reported,
            'is_hidden': self.is_hidden,
            'hidden_reason': self.hidden_reason,
            'likes_count': self.likes_count,
            'replies_count': self.replies_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relations:
            result['likes'] = [like.to_dict() for like in self.likes]
            result['reports'] = [report.to_dict() for report in self.reports]

        return result


class MovieCommentLike(Base):
    """Modelo para likes de comentarios"""

    __tablename__ = "movie_comment_likes"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("movie_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relaciones
    comment = relationship("MovieComment", back_populates="likes")

    __table_args__ = (
        UniqueConstraint('comment_id', 'user_id', name='uq_comment_user_like'),
    )

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'comment_id': self.comment_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class MovieCommentReport(Base):
    """Modelo para reportes de comentarios"""

    __tablename__ = "movie_comment_reports"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("movie_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relaciones
    comment = relationship("MovieComment", back_populates="reports")

    __table_args__ = (
        UniqueConstraint('comment_id', 'user_id', name='uq_comment_user_report'),
    )

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'comment_id': self.comment_id,
            'user_id': self.user_id,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# Índices para optimización de consultas
Index('idx_movie_comments_movie_id_created', MovieComment.movie_id, MovieComment.created_at.desc())
Index('idx_movie_comments_parent_id', MovieComment.parent_comment_id, MovieComment.created_at.desc())
Index('idx_movie_comments_likes_count', MovieComment.likes_count.desc())
