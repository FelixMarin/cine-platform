"""
Caso de uso para obtener comentarios de una película
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from src.domain.ports.out.comment_repository_port import CommentRepositoryPort


class GetCommentsPort(ABC):
    """Puerto de entrada para obtener comentarios"""

    @abstractmethod
    def execute(
        self,
        movie_id: int,
        limit: int,
        offset: int,
        include_hidden: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Obtiene comentarios de una película con paginación"""
        pass


class GetCommentsUseCase(GetCommentsPort):
    """Caso de uso para obtener comentarios"""

    def __init__(self, comment_repository: CommentRepositoryPort):
        self._comment_repository = comment_repository

    def execute(
        self,
        movie_id: int,
        limit: int,
        offset: int,
        include_hidden: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        # Validaciones
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100
        if offset < 0:
            offset = 0

        # Obtener comentarios
        comments, total = self._comment_repository.get_comments_by_movie(
            movie_id=movie_id,
            limit=limit,
            offset=offset,
            include_hidden=include_hidden
        )

        # Convertir a diccionarios
        return [comment.to_dict() for comment in comments], total
