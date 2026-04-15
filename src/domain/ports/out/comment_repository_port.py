"""
Puerto de salida para operaciones con comentarios
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.domain.models.comment import Comment


class CommentRepositoryPort(ABC):
    """Puerto de salida para operaciones con comentarios"""

    @abstractmethod
    def get_comments_by_movie(
        self,
        movie_id: int,
        limit: int,
        offset: int,
        include_hidden: bool = False
    ) -> Tuple[List[Comment], int]:
        """Obtiene comentarios de una película con paginación"""
        pass

    @abstractmethod
    def get_replies(
        self,
        comment_id: int,
        limit: int,
        offset: int
    ) -> List[Comment]:
        """Obtiene respuestas a un comentario"""
        pass

    @abstractmethod
    def add_comment(
        self,
        user_id: int,
        movie_id: int,
        movie_title: str,
        comment_text: str,
        parent_comment_id: Optional[int],
        is_spoiler: bool,
        tmdb_id: Optional[int] = None
    ) -> Comment:
        """Añade un nuevo comentario"""
        pass

    @abstractmethod
    def update_comment(
        self,
        comment_id: int,
        user_id: int,
        comment_text: str,
        is_spoiler: bool
    ) -> Comment:
        """Actualiza un comentario existente"""
        pass

    @abstractmethod
    def delete_comment(
        self,
        comment_id: int,
        user_id: int,
        is_admin: bool
    ) -> bool:
        """Elimina un comentario (lógica o físicamente)"""
        pass

    @abstractmethod
    def get_comment_by_id(self, comment_id: int) -> Optional[Comment]:
        """Obtiene un comentario por ID"""
        pass

    @abstractmethod
    def toggle_like(
        self,
        comment_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        """Añade o quita like, devuelve (liked, nuevos_likes_count)"""
        pass

    @abstractmethod
    def report_comment(
        self,
        comment_id: int,
        user_id: int,
        reason: str
    ) -> bool:
        """Reporta un comentario"""
        pass

    @abstractmethod
    def hide_comment(
        self,
        comment_id: int,
        reason: str,
        is_admin: bool
    ) -> bool:
        """Oculta un comentario (solo admin)"""
        pass

    @abstractmethod
    def get_user_liked_comments(
        self,
        comment_ids: List[int],
        user_id: int
    ) -> List[int]:
        """Obtiene los IDs de comentarios que le gustan al usuario"""
        pass
