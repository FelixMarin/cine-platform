"""
Caso de uso para eliminar un comentario
"""

from abc import ABC, abstractmethod
from src.domain.ports.out.comment_repository_port import CommentRepositoryPort


class DeleteCommentPort(ABC):
    """Puerto de entrada para eliminar un comentario"""

    @abstractmethod
    def execute(
        self,
        comment_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> bool:
        """Elimina un comentario existente"""
        pass


class DeleteCommentUseCase(DeleteCommentPort):
    """Caso de uso para eliminar un comentario"""

    def __init__(self, comment_repository: CommentRepositoryPort):
        self._comment_repository = comment_repository

    def execute(
        self,
        comment_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> bool:
        # Verificar que el comentario existe
        existing = self._comment_repository.get_comment_by_id(comment_id)
        if not existing:
            raise ValueError("El comentario no existe")

        # Verificar permisos (dueño o admin)
        if not is_admin and existing.user_id != user_id:
            raise PermissionError("No tienes permiso para eliminar este comentario")

        # Eliminar el comentario
        return self._comment_repository.delete_comment(
            comment_id=comment_id,
            user_id=user_id,
            is_admin=is_admin
        )