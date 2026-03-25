"""
Repositorio para comentarios de películas
Implementación con SQLAlchemy
"""

from datetime import datetime
from typing import Optional, List, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from src.infrastructure.models.comment import MovieComment, MovieCommentLike, MovieCommentReport
from src.domain.models.comment import Comment as DomainComment
from src.domain.ports.out.comment_repository_port import CommentRepositoryPort
from src.adapters.outgoing.repositories.cine.app_user_repository import AppUserRepository

logger = logging.getLogger(__name__)


class CommentRepository(CommentRepositoryPort):
    """Repositorio para gestionar comentarios de películas"""

    def __init__(self, db: Session):
        self._db = db
        self._user_repo = AppUserRepository()

    def _to_domain_comment(
        self, 
        db_comment: MovieComment, 
        current_user_id: int = 0,
        include_replies: bool = False
    ) -> DomainComment:
        """Convierte un modelo de DB a modelo de dominio"""
        
        # Obtener información del usuario
        user_info = self._user_repo.get_by_id(db_comment.user_id)
        username = user_info.get('username', 'Usuario') if user_info else 'Usuario'
        avatar_url = user_info.get('avatar_url') if user_info else None
        
        # Obtener replies si se solicita
        replies = None
        if include_replies:
            replies_db = self._db.query(MovieComment).filter(
                MovieComment.parent_comment_id == db_comment.id,
                MovieComment.is_hidden == False
            ).order_by(MovieComment.created_at.asc()).all()
            replies = [
                self._to_domain_comment(r, current_user_id, include_replies=False)
                for r in replies_db
            ]
        
        # Permisos de edición/eliminación
        can_edit = db_comment.user_id == current_user_id if current_user_id else False
        can_delete = db_comment.user_id == current_user_id if current_user_id else False
        
        return DomainComment(
            id=db_comment.id,
            user_id=db_comment.user_id,
            username=username,
            avatar_url=avatar_url,
            movie_id=db_comment.movie_id,
            movie_title=db_comment.movie_title,
            tmdb_id=db_comment.tmdb_id,
            comment_text=db_comment.comment_text,
            parent_comment_id=db_comment.parent_comment_id,
            is_spoiler=db_comment.is_spoiler,
            is_edited=db_comment.is_edited,
            likes_count=db_comment.likes_count,
            replies_count=db_comment.replies_count,
            is_reported=db_comment.is_reported,
            is_hidden=db_comment.is_hidden,
            hidden_reason=db_comment.hidden_reason,
            created_at=db_comment.created_at,
            updated_at=db_comment.updated_at,
            can_edit=can_edit,
            can_delete=can_delete,
            replies=replies
        )

    def get_comments_by_movie(
        self, 
        movie_id: int, 
        limit: int, 
        offset: int, 
        include_hidden: bool = False
    ) -> Tuple[List[DomainComment], int]:
        """Obtiene comentarios de una película con paginación"""
        
        # Query base
        query = self._db.query(MovieComment).filter(
            MovieComment.movie_id == movie_id
        )
        
        # Filtrar comentarios principales (no respuestas)
        query = query.filter(MovieComment.parent_comment_id == None)
        
        # Filtrar ocultos si no es admin
        if not include_hidden:
            query = query.filter(MovieComment.is_hidden == False)
        
        # Contar total
        total = query.count()
        
        # Obtener comentarios
        comments_db = query.order_by(
            MovieComment.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Convertir a dominio
        comments = [
            self._to_domain_comment(c, include_replies=True)
            for c in comments_db
        ]
        
        return comments, total

    def get_replies(
        self, 
        comment_id: int, 
        limit: int, 
        offset: int
    ) -> List[DomainComment]:
        """Obtiene respuestas a un comentario"""
        
        replies_db = self._db.query(MovieComment).filter(
            MovieComment.parent_comment_id == comment_id,
            MovieComment.is_hidden == False
        ).order_by(MovieComment.created_at.asc()).offset(offset).limit(limit).all()
        
        return [self._to_domain_comment(r) for r in replies_db]

    def add_comment(
        self,
        user_id: int,
        movie_id: int,
        movie_title: str,
        comment_text: str,
        parent_comment_id: Optional[int],
        is_spoiler: bool,
        tmdb_id: Optional[int] = None
    ) -> DomainComment:
        """Añade un nuevo comentario"""
        
        # Crear el comentario
        new_comment = MovieComment(
            user_id=user_id,
            movie_id=movie_id,
            movie_title=movie_title,
            tmdb_id=tmdb_id,
            comment_text=comment_text,
            parent_comment_id=parent_comment_id,
            is_spoiler=is_spoiler,
            is_edited=False,
            likes_count=0,
            replies_count=0
        )
        
        self._db.add(new_comment)
        self._db.flush()
        
        # Si es respuesta, actualizar contador del padre
        if parent_comment_id:
            parent = self._db.query(MovieComment).filter(
                MovieComment.id == parent_comment_id
            ).first()
            if parent:
                parent.replies_count += 1
        
        self._db.commit()
        self._db.refresh(new_comment)
        
        return self._to_domain_comment(new_comment)

    def update_comment(
        self,
        comment_id: int,
        user_id: int,
        comment_text: str,
        is_spoiler: bool
    ) -> DomainComment:
        """Actualiza un comentario existente"""
        
        comment = self._db.query(MovieComment).filter(
            MovieComment.id == comment_id
        ).first()
        
        if not comment:
            raise ValueError("Comentario no encontrado")
        
        comment.comment_text = comment_text
        comment.is_spoiler = is_spoiler
        comment.is_edited = True
        comment.updated_at = datetime.utcnow()
        
        self._db.commit()
        self._db.refresh(comment)
        
        return self._to_domain_comment(comment)

    def delete_comment(
        self,
        comment_id: int,
        user_id: int,
        is_admin: bool
    ) -> bool:
        """Elimina un comentario (eliminación lógica si tiene respuestas, física si no)"""
        
        comment = self._db.query(MovieComment).filter(
            MovieComment.id == comment_id
        ).first()
        
        if not comment:
            raise ValueError("Comentario no encontrado")
        
        # Verificar permisos
        if not is_admin and comment.user_id != user_id:
            raise PermissionError("No tienes permiso para eliminar este comentario")
        
        # Si tiene respuestas, ocultar en lugar de eliminar
        if comment.replies_count > 0:
            comment.is_hidden = True
            comment.hidden_reason = "Eliminado por el usuario"
            self._db.commit()
        else:
            # Eliminar físicamente
            self._db.delete(comment)
            self._db.commit()
        
        return True

    def get_comment_by_id(self, comment_id: int) -> Optional[DomainComment]:
        """Obtiene un comentario por ID"""
        
        comment = self._db.query(MovieComment).filter(
            MovieComment.id == comment_id
        ).first()
        
        if not comment:
            return None
        
        return self._to_domain_comment(comment)

    def toggle_like(
        self,
        comment_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        """Añade o quita like, devuelve (liked, nuevos_likes_count)"""
        
        # Verificar si ya existe el like
        existing_like = self._db.query(MovieCommentLike).filter(
            MovieCommentLike.comment_id == comment_id,
            MovieCommentLike.user_id == user_id
        ).first()
        
        comment = self._db.query(MovieComment).filter(
            MovieComment.id == comment_id
        ).first()
        
        if not comment:
            raise ValueError("Comentario no encontrado")
        
        if existing_like:
            # Quitar like
            self._db.delete(existing_like)
            comment.likes_count = max(0, comment.likes_count - 1)
            liked = False
        else:
            # Añadir like
            new_like = MovieCommentLike(
                comment_id=comment_id,
                user_id=user_id
            )
            self._db.add(new_like)
            comment.likes_count += 1
            liked = True
        
        self._db.commit()
        
        return liked, comment.likes_count

    def report_comment(
        self,
        comment_id: int,
        user_id: int,
        reason: str
    ) -> bool:
        """Reporta un comentario"""
        
        # Verificar si ya existe el reporte
        existing_report = self._db.query(MovieCommentReport).filter(
            MovieCommentReport.comment_id == comment_id,
            MovieCommentReport.user_id == user_id
        ).first()
        
        if existing_report:
            raise ValueError("Ya has reportado este comentario")
        
        comment = self._db.query(MovieComment).filter(
            MovieComment.id == comment_id
        ).first()
        
        if not comment:
            raise ValueError("Comentario no encontrado")
        
        # Crear reporte
        report = MovieCommentReport(
            comment_id=comment_id,
            user_id=user_id,
            reason=reason
        )
        self._db.add(report)
        
        # Marcar comentario como reportado
        comment.is_reported = True
        
        self._db.commit()
        
        return True

    def hide_comment(
        self,
        comment_id: int,
        reason: str,
        is_admin: bool
    ) -> bool:
        """Oculta un comentario (solo admin)"""
        
        if not is_admin:
            raise PermissionError("Solo los administradores pueden ocultar comentarios")
        
        comment = self._db.query(MovieComment).filter(
            MovieComment.id == comment_id
        ).first()
        
        if not comment:
            raise ValueError("Comentario no encontrado")
        
        comment.is_hidden = True
        comment.hidden_reason = reason
        
        self._db.commit()
        
        return True

    def get_user_liked_comments(
        self,
        comment_ids: List[int],
        user_id: int
    ) -> List[int]:
        """Obtiene los IDs de comentarios que le gustan al usuario"""
        
        likes = self._db.query(MovieCommentLike).filter(
            MovieCommentLike.comment_id.in_(comment_ids),
            MovieCommentLike.user_id == user_id
        ).all()
        
        return [like.comment_id for like in likes]