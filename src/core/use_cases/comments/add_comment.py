"""
Caso de uso para añadir un nuevo comentario
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from src.domain.ports.out.comment_repository_port import CommentRepositoryPort


class AddCommentPort(ABC):
    """Puerto de entrada para añadir un nuevo comentario"""

    @abstractmethod
    def execute(
        self,
        user_id: int,
        movie_id: int,
        movie_title: str,
        comment_text: str,
        parent_comment_id: Optional[int],
        is_spoiler: bool,
        tmdb_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Añade un nuevo comentario y retorna el resultado"""
        pass


class AddCommentUseCase(AddCommentPort):
    """Caso de uso para añadir un nuevo comentario"""

    def __init__(self, comment_repository: CommentRepositoryPort):
        self._comment_repository = comment_repository

    def execute(
        self,
        user_id: int,
        movie_id: int,
        movie_title: str,
        comment_text: str,
        parent_comment_id: Optional[int],
        is_spoiler: bool,
        tmdb_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # Validaciones
        if not comment_text or len(comment_text.strip()) < 3:
            raise ValueError("El comentario debe tener al menos 3 caracteres")

        if len(comment_text) > 2000:
            raise ValueError("El comentario no puede exceder los 2000 caracteres")

        # Si es respuesta, verificar que el comentario padre existe
        if parent_comment_id:
            parent = self._comment_repository.get_comment_by_id(parent_comment_id)
            if not parent:
                raise ValueError("El comentario al que respondes no existe")
            if parent.movie_id != movie_id:
                raise ValueError("No puedes responder a un comentario de otra película")

        # Crear el comentario
        comment = self._comment_repository.add_comment(
            user_id=user_id,
            movie_id=movie_id,
            movie_title=movie_title,
            comment_text=comment_text,
            parent_comment_id=parent_comment_id,
            is_spoiler=is_spoiler,
            tmdb_id=tmdb_id
        )

        return comment.to_dict()