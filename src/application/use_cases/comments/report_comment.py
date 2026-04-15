"""
Caso de uso para reportar un comentario
"""

from abc import ABC, abstractmethod

from src.domain.ports.out.comment_repository_port import CommentRepositoryPort


class ReportCommentPort(ABC):
    """Puerto de entrada para reportar un comentario"""

    @abstractmethod
    def execute(
        self,
        comment_id: int,
        user_id: int,
        reason: str
    ) -> bool:
        """Reporta un comentario por contenido inapropiado"""
        pass


class ReportCommentUseCase(ReportCommentPort):
    """Caso de uso para reportar un comentario"""

    def __init__(self, comment_repository: CommentRepositoryPort):
        self._comment_repository = comment_repository

    def execute(
        self,
        comment_id: int,
        user_id: int,
        reason: str
    ) -> bool:
        # Validaciones
        if not reason or len(reason.strip()) < 5:
            raise ValueError("El motivo del reporte debe tener al menos 5 caracteres")

        if len(reason) > 500:
            raise ValueError("El motivo del reporte no puede exceder los 500 caracteres")

        # Verificar que el comentario existe
        existing = self._comment_repository.get_comment_by_id(comment_id)
        if not existing:
            raise ValueError("El comentario no existe")

        # No puedes reportar tu propio comentario
        if existing.user_id == user_id:
            raise ValueError("No puedes reportar tu propio comentario")

        # Reportar el comentario
        return self._comment_repository.report_comment(
            comment_id=comment_id,
            user_id=user_id,
            reason=reason
        )
