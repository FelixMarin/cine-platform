"""
Modelo de dominio para comentarios de películas
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Comment:
    """Modelo de dominio para comentarios de películas"""
    id: int
    user_id: int
    username: str
    avatar_url: Optional[str]
    movie_id: int
    movie_title: str
    tmdb_id: Optional[int]
    comment_text: str
    parent_comment_id: Optional[int]
    is_spoiler: bool
    is_edited: bool
    likes_count: int
    replies_count: int
    is_reported: bool
    is_hidden: bool
    hidden_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False
    can_delete: bool = False
    replies: Optional[List['Comment']] = None

    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'avatar_url': self.avatar_url,
            'movie_id': self.movie_id,
            'movie_title': self.movie_title,
            'tmdb_id': self.tmdb_id,
            'comment_text': self.comment_text,
            'parent_comment_id': self.parent_comment_id,
            'is_spoiler': self.is_spoiler,
            'is_edited': self.is_edited,
            'likes_count': self.likes_count,
            'replies_count': self.replies_count,
            'is_reported': self.is_reported,
            'is_hidden': self.is_hidden,
            'hidden_reason': self.hidden_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'can_edit': self.can_edit,
            'can_delete': self.can_delete,
            'replies': [reply.to_dict() for reply in self.replies] if self.replies else []
        }
