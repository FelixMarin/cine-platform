"""
Blueprint para endpoints de comentarios de películas
"""

import logging

from flask import Blueprint, jsonify, request, session

from src.adapters.config.dependencies import get_comment_repository
from src.application.use_cases.comments.add_comment import AddCommentUseCase
from src.application.use_cases.comments.delete_comment import DeleteCommentUseCase
from src.application.use_cases.comments.edit_comment import EditCommentUseCase
from src.application.use_cases.comments.get_comments import GetCommentsUseCase
from src.application.use_cases.comments.like_comment import LikeCommentUseCase
from src.application.use_cases.comments.report_comment import ReportCommentUseCase

logger = logging.getLogger(__name__)

comments_bp = Blueprint("comments", __name__, url_prefix="/api")


def get_user_id() -> int:
    """Obtiene el ID del usuario actual de la sesión"""
    return session.get("user_id", 0)


def is_admin() -> bool:
    """Verifica si el usuario actual es administrador"""
    return session.get("user_role") == "admin"


def is_authenticated() -> bool:
    """Verifica si el usuario está autenticado"""
    return get_user_id() > 0


@comments_bp.route("/movie/comments", methods=["GET"])
def get_movie_comments():
    """
    Obtiene comentarios de una película
    
    Query params:
        - movie_id: ID de la película (requerido)
        - limit: Límite de comentarios (default: 20)
        - offset: Offset para paginación (default: 0)
    
    Returns:
        JSON con comments, total y has_more
    """
    movie_id = request.args.get("movie_id", type=int)
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    if not movie_id:
        return jsonify({"error": "movie_id es requerido"}), 400

    try:
        with get_comment_repository() as repo:
            use_case = GetCommentsUseCase(repo)
            current_user_id = get_user_id()
            comments, total = use_case.execute(
                movie_id=movie_id,
                limit=limit,
                offset=offset,
                include_hidden=is_admin()
            )

            # Agregar información de likes del usuario actual
            if current_user_id > 0 and comments:
                comment_ids = [c['id'] for c in comments]
                liked_ids = repo.get_user_liked_comments(comment_ids, current_user_id)
                for comment in comments:
                    comment['user_liked'] = comment['id'] in liked_ids

            return jsonify({
                "comments": comments,
                "total": total,
                "has_more": offset + limit < total
            })
    except Exception as e:
        logger.error(f"Error obteniendo comentarios: {e}")
        return jsonify({"error": str(e)}), 500


@comments_bp.route("/movie/comment", methods=["POST"])
def add_comment():
    """
    Añade un nuevo comentario
    
    Body params:
        - movie_id: ID de la película (requerido)
        - movie_title: Título de la película (requerido)
        - tmdb_id: ID de TMDB (opcional)
        - comment_text: Texto del comentario (requerido)
        - parent_comment_id: ID del comentario padre para respuestas (opcional)
        - is_spoiler: Boolean indicando si contiene spoiler (default: false)
    
    Returns:
        JSON con el comentario creado
    """
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401

    data = request.get_json()

    # Validar campos requeridos
    required = ["movie_id", "movie_title", "comment_text"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} es requerido"}), 400

    try:
        with get_comment_repository() as repo:
            use_case = AddCommentUseCase(repo)
            comment = use_case.execute(
                user_id=user_id,
                movie_id=data["movie_id"],
                movie_title=data["movie_title"],
                comment_text=data["comment_text"],
                parent_comment_id=data.get("parent_comment_id"),
                is_spoiler=data.get("is_spoiler", False),
                tmdb_id=data.get("tmdb_id")
            )
            comment['user_liked'] = False
            return jsonify(comment), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error añadiendo comentario: {e}")
        return jsonify({"error": str(e)}), 500


@comments_bp.route("/movie/comment/<int:comment_id>", methods=["PUT"])
def edit_comment(comment_id):
    """
    Edita un comentario existente
    
    Body params:
        - comment_text: Nuevo texto del comentario (requerido)
        - is_spoiler: Boolean indicando si contiene spoiler (default: false)
    
    Returns:
        JSON con el comentario actualizado
    """
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401

    data = request.get_json()

    if "comment_text" not in data:
        return jsonify({"error": "comment_text es requerido"}), 400

    try:
        with get_comment_repository() as repo:
            use_case = EditCommentUseCase(repo)
            comment = use_case.execute(
                comment_id=comment_id,
                user_id=user_id,
                comment_text=data["comment_text"],
                is_spoiler=data.get("is_spoiler", False),
                is_admin=is_admin()
            )
            return jsonify(comment)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error editando comentario: {e}")
        return jsonify({"error": str(e)}), 500


@comments_bp.route("/movie/comment/<int:comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    """
    Elimina un comentario
    
    Returns:
        JSON con success=true si se eliminó correctamente
    """
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401

    try:
        with get_comment_repository() as repo:
            use_case = DeleteCommentUseCase(repo)
            success = use_case.execute(
                comment_id=comment_id,
                user_id=user_id,
                is_admin=is_admin()
            )
            if success:
                return jsonify({"success": True})
            return jsonify({"error": "No se pudo eliminar"}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error eliminando comentario: {e}")
        return jsonify({"error": str(e)}), 500


@comments_bp.route("/movie/comment/<int:comment_id>/like", methods=["POST"])
def toggle_like(comment_id):
    """
    Da o quita like a un comentario
    
    Returns:
        JSON con liked y likes_count
    """
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401

    try:
        with get_comment_repository() as repo:
            use_case = LikeCommentUseCase(repo)
            liked, likes_count = use_case.execute(
                comment_id=comment_id,
                user_id=user_id
            )
            return jsonify({"liked": liked, "likes_count": likes_count})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error dando like: {e}")
        return jsonify({"error": str(e)}), 500


@comments_bp.route("/movie/comment/<int:comment_id>/report", methods=["POST"])
def report_comment(comment_id):
    """
    Reporta un comentario por contenido inapropiado
    
    Body params:
        - reason: Motivo del reporte (requerido)
    
    Returns:
        JSON con success=true si se reportó correctamente
    """
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401

    data = request.get_json()
    reason = data.get("reason", "")

    if not reason:
        return jsonify({"error": "Motivo del reporte es requerido"}), 400

    try:
        with get_comment_repository() as repo:
            use_case = ReportCommentUseCase(repo)
            success = use_case.execute(
                comment_id=comment_id,
                user_id=user_id,
                reason=reason
            )
            return jsonify({"success": success})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error reportando comentario: {e}")
        return jsonify({"error": str(e)}), 500


@comments_bp.route("/movie/comments/replies/<int:comment_id>", methods=["GET"])
def get_replies(comment_id):
    """
    Obtiene las respuestas a un comentario
    
    Query params:
        - limit: Límite de respuestas (default: 20)
        - offset: Offset para paginación (default: 0)
    
    Returns:
        JSON con replies y total
    """
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    try:
        with get_comment_repository() as repo:
            replies = repo.get_replies(
                comment_id=comment_id,
                limit=limit,
                offset=offset
            )

            current_user_id = get_user_id()
            if current_user_id > 0 and replies:
                reply_ids = [r.id for r in replies]
                liked_ids = repo.get_user_liked_comments(reply_ids, current_user_id)
                for reply in replies:
                    reply.can_edit = reply.user_id == current_user_id
                    reply.can_delete = reply.user_id == current_user_id or is_admin()
                    reply.user_liked = reply.id in liked_ids

            return jsonify({
                "replies": [r.to_dict() for r in replies],
                "total": len(replies)
            })
    except Exception as e:
        logger.error(f"Error obteniendo respuestas: {e}")
        return jsonify({"error": str(e)}), 500
