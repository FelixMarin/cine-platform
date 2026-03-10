"""
Adaptador de entrada - Rutas de perfil de usuario
Blueprint para /api/profile
"""

from flask import Blueprint, jsonify, request, session
from src.core.services.UserSyncService import UserSyncService
from src.adapters.outgoing.repositories.cine.app_user_repository import (
    AppUserRepository,
)
import logging
import os
import uuid
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__)

_user_sync_service = None

AVATAR_UPLOAD_FOLDER = os.path.join("static", "uploads", "avatars")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


def allowed_file(filename):
    if not filename:
        return False
    parts = filename.rsplit(".", 1)
    if len(parts) != 2:
        return False
    return parts[1].lower() in ALLOWED_EXTENSIONS


def get_user_sync_service():
    """Obtiene o inicializa el servicio de sincronización"""
    global _user_sync_service
    if _user_sync_service is None:
        try:
            repo = AppUserRepository()
            _user_sync_service = UserSyncService(repo)
        except Exception as e:
            logger.error(f"[Profile] Error inicializando servicio: {e}")
            return None
    return _user_sync_service


def require_app_user(f):
    """Decorador para requerir app_user_id en sesión"""

    def wrapper(*args, **kwargs):
        app_user_id = session.get("app_user_id")
        if not app_user_id:
            return jsonify({"success": False, "error": "No autenticado"}), 401
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@profile_bp.route("/api/profile/me", methods=["GET"])
def get_my_profile():
    """Obtiene el perfil del usuario actual"""
    try:
        app_user_id = session.get("app_user_id")

        if not app_user_id:
            # Intentar obtener datos básicos de la sesión
            return jsonify(
                {
                    "success": True,
                    "profile": {
                        "username": session.get("username"),
                        "email": session.get("email"),
                        "display_name": session.get("display_name"),
                        "avatar_url": session.get("avatar_url"),
                        "bio": None,
                        "privacy_level": "public",
                    },
                }
            )

        service = get_user_sync_service()
        if not service:
            return jsonify({"success": False, "error": "Servicio no disponible"}), 500

        profile = service.get_user_profile(app_user_id)

        if not profile:
            return jsonify({"success": False, "error": "Perfil no encontrado"}), 404

        return jsonify(
            {
                "success": True,
                "profile": {
                    "id": profile.get("id"),
                    "username": profile.get("username"),
                    "email": profile.get("email"),
                    "display_name": profile.get("display_name"),
                    "avatar_url": profile.get("avatar_url"),
                    "bio": profile.get("bio"),
                    "privacy_level": profile.get("privacy_level", "public"),
                    "created_at": str(profile.get("created_at"))
                    if profile.get("created_at")
                    else None,
                    "last_active": str(profile.get("last_active"))
                    if profile.get("last_active")
                    else None,
                },
            }
        )

    except Exception as e:
        logger.error(f"[Profile] Error obteniendo perfil: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@profile_bp.route("/api/profile/update", methods=["POST"])
def update_my_profile():
    """Actualiza el perfil del usuario actual"""
    try:
        app_user_id = session.get("app_user_id")

        if not app_user_id:
            return jsonify({"success": False, "error": "No autenticado"}), 401

        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Datos inválidos"}), 400

        service = get_user_sync_service()
        if not service:
            return jsonify({"success": False, "error": "Servicio no disponible"}), 500

        success = service.update_user_profile(app_user_id, data)

        if success:
            # Actualizar sesión si cambió display_name
            if data.get("display_name"):
                session["display_name"] = data.get("display_name")

            return jsonify({"success": True, "message": "Perfil actualizado"})
        else:
            return jsonify({"success": False, "error": "No se pudo actualizar"}), 500

    except Exception as e:
        logger.error(f"[Profile] Error actualizando perfil: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@profile_bp.route("/api/profile/avatar", methods=["POST"])
def upload_avatar():
    """Sube una nueva imagen de avatar"""
    app_user_id = session.get("app_user_id")

    if not app_user_id:
        return jsonify({"success": False, "error": "Usuario no autenticado"}), 401

    if "avatar" not in request.files:
        return jsonify({"success": False, "error": "No se envió ningún archivo"}), 400

    file = request.files["avatar"]

    if file.filename == "":
        return jsonify({"success": False, "error": "Nombre de archivo vacío"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {"success": False, "error": "Formato no permitido. Usa JPG, PNG o GIF"}
        ), 400

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)

    if file_length > MAX_AVATAR_SIZE:
        return jsonify(
            {"success": False, "error": "La imagen no puede superar los 2MB"}
        ), 400

    os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)

    filename_orig = file.filename
    if not filename_orig or "." not in filename_orig:
        return jsonify({"success": False, "error": "Nombre de archivo inválido"}), 400

    parts = filename_orig.rsplit(".", 1)
    ext = parts[1].lower() if len(parts) == 2 else "jpg"
    filename = f"avatar_{app_user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(AVATAR_UPLOAD_FOLDER, filename)

    file.save(filepath)

    avatar_url = f"/static/uploads/avatars/{filename}"

    try:
        repo = AppUserRepository()
        repo.update_profile(app_user_id, {"avatar_url": avatar_url})

        session["avatar_url"] = avatar_url

        return jsonify(
            {
                "success": True,
                "avatar_url": avatar_url,
                "message": "Avatar actualizado correctamente",
            }
        )
    except Exception as e:
        logger.error(f"[Profile] Error guardando avatar: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
