"""
Caso de uso para dar like a un comentario
"""

from typing import Tuple
from abc import ABC, abstractmethod
from src.domain.ports.out.comment_repository_port import CommentRepositoryPort


class LikeCommentPort(ABC):
    """Puerto de entrada para dar like a un comentario"""

    @abstractmethod
    def execute(
        self,
        comment_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        """Da o quita like a un comentario. Retorna (liked, likes_count)"""
        pass


class LikeCommentUseCase(LikeCommentPort):
    """Caso de uso para dar like a un comentario"""

    def __init__(self, comment_repository: CommentRepositoryPort):
        self._comment_repository = comment_repository

    def execute(
        self,
        comment_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        # Verificar que el comentario existe
        existing = self._comment_repository.get_comment_by_id(comment_id)
        if not existing:
            raise ValueError("El comentario no existe")

        # Toggle like
        liked, likes_count = self._comment_repository.toggle_like(
            comment_id=comment_id,
            user_id=user_id
        )

        return liked, likes_count