"""
Caso de uso para editar un comentario
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.domain.ports.out.comment_repository_port import CommentRepositoryPort


class EditCommentPort(ABC):
    """Puerto de entrada para editar un comentario"""

    @abstractmethod
    def execute(
        self,
        comment_id: int,
        user_id: int,
        comment_text: str,
        is_spoiler: bool,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Edita un comentario existente"""
        pass


class EditCommentUseCase(EditCommentPort):
    """Caso de uso para editar un comentario"""

    def __init__(self, comment_repository: CommentRepositoryPort):
        self._comment_repository = comment_repository

    def execute(
        self,
        comment_id: int,
        user_id: int,
        comment_text: str,
        is_spoiler: bool,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        # Validaciones
        if not comment_text or len(comment_text.strip()) < 3:
            raise ValueError("El comentario debe tener al menos 3 caracteres")

        if len(comment_text) > 2000:
            raise ValueError("El comentario no puede exceder los 2000 caracteres")

        # Verificar que el comentario existe
        existing = self._comment_repository.get_comment_by_id(comment_id)
        if not existing:
            raise ValueError("El comentario no existe")

        # Verificar permisos (dueño o admin)
        if not is_admin and existing.user_id != user_id:
            raise PermissionError("No tienes permiso para editar este comentario")

        # Actualizar el comentario
        comment = self._comment_repository.update_comment(
            comment_id=comment_id,
            user_id=user_id,
            comment_text=comment_text,
            is_spoiler=is_spoiler
        )

        return comment.to_dict()
