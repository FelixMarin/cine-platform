"""
Adaptador de entrada - Rutas de perfil de usuario
Blueprint para /api/profile
"""

from flask import Blueprint, jsonify, request, session, current_app
from src.core.services.UserSyncService import UserSyncService
from src.adapters.outgoing.repositories.cine.app_user_repository import (
    AppUserRepository,
)
import logging
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")

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
        app_user_id = session.get("app_user_id") or session.get("user_id")
        if not app_user_id:
            return jsonify({"success": False, "error": "No autenticado"}), 401
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@profile_bp.route("/me", methods=["GET"])
def get_my_profile():
    """Obtiene el perfil del usuario actual desde la base de datos"""
    try:
        app_user_id = session.get("app_user_id")
        user_id = session.get("user_id")

        logger.info(
            f"[Profile] get_my_profile - app_user_id from session: {app_user_id} (type: {type(app_user_id)})"
        )
        logger.info(
            f"[Profile] get_my_profile - user_id from session: {user_id} (type: {type(user_id)})"
        )

        app_user_id = app_user_id or user_id

        if not app_user_id:
            # Fallback: intentar obtener datos básicos de la sesión
            logger.warning("[Profile] No app_user_id in session, using session data")
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

        # Obtener servicio y perfil desde BD
        service = get_user_sync_service()
        if not service:
            # Fallback: usar datos de sesión si el servicio no está disponible
            logger.warning(
                "[Profile] UserSyncService not available, using session data"
            )
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

        # Convertir a int si es string
        lookup_id: int = app_user_id
        if isinstance(app_user_id, str):
            try:
                lookup_id = int(app_user_id)
                logger.info(
                    f"[Profile] Converted app_user_id string to int: {lookup_id}"
                )
            except (ValueError, TypeError):
                logger.warning(
                    f"[Profile] Could not convert app_user_id to int: {app_user_id}"
                )
                # Dejar como string si no se puede convertir

        profile = service.get_user_profile(lookup_id)

        # logger.info(f"[Profile] get_user_profile result: {profile}")

        if not profile:
            # Fallback: usar datos de sesión si el perfil no existe en BD
            logger.warning(
                f"[Profile] Profile not found for app_user_id: {app_user_id}"
            )
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

        # Log para depuración
        logger.info(
            f"[Profile] Perfil obtenido: id={profile.get('id')}, username={profile.get('username')}, email={profile.get('email')}"
        )

        return jsonify(
            {
                "success": True,
                "profile": {
                    "id": profile.get("id"),
                    "username": profile.get("username"),
                    "email": profile.get("email"),  # ← VIENE DE BD
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
        # Fallback: usar datos de sesión en caso de error
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


@profile_bp.route("/update", methods=["POST"])
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


@profile_bp.route("/avatar", methods=["POST"])
def upload_avatar():
    """Sube una nueva imagen de avatar"""
    import os
    from flask import current_app

    app_user_id = session.get("app_user_id") or session.get("user_id")

    # LOG 1: Información de la sesión
    # logger.info(f"[Avatar] ===== INICIO SUBIDA AVATAR =====")
    # logger.info(f"[Avatar] app_user_id: {app_user_id}")
    # logger.info(f"[Avatar] session keys: {list(session.keys())}")

    # LOG 2: Información del directorio
    # logger.info(f"[Avatar] current_app.root_path: {current_app.root_path}")
    # logger.info(f"[Avatar] Directorio actual: {os.getcwd()}")
    # logger.info(f"[Avatar] AVATAR_UPLOAD_FOLDER definido como: {AVATAR_UPLOAD_FOLDER}")

    # LOG 3: Verificar si el directorio existe
    abs_folder = os.path.abspath(
        os.path.join(current_app.root_path, "static", "uploads", "avatars")
    )
    # logger.info(f"[Avatar] Ruta absoluta del folder: {abs_folder}")
    # logger.info(f"[Avatar] ¿Existe el folder? {os.path.exists(abs_folder)}")

    if os.path.exists(abs_folder):
        logger.info(
            f"[Avatar] Permisos del folder: {oct(os.stat(abs_folder).st_mode)[-3:]}"
        )
        logger.info(
            f"[Avatar] Contenido del folder: {os.listdir(abs_folder) if os.path.exists(abs_folder) else []}"
        )

    if not app_user_id:
        logger.warning(f"[Avatar] Usuario no autenticado")
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

    # Usar ruta absoluta basada en el directorio de la aplicación Flask
    base_dir = os.path.abspath(current_app.root_path)
    upload_folder = os.path.join(base_dir, "static", "uploads", "avatars")
    os.makedirs(upload_folder, exist_ok=True)

    # logger.info(f"[Profile] Directorio de uploads: {upload_folder}")

    filename_orig = file.filename
    if not filename_orig or "." not in filename_orig:
        return jsonify({"success": False, "error": "Nombre de archivo inválido"}), 400

    parts = filename_orig.rsplit(".", 1)
    ext = parts[1].lower() if len(parts) == 2 else "jpg"
    filename = f"avatar_{app_user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(upload_folder, filename)

    # LOG 4: Antes de guardar
    # logger.info(f"[Avatar] Nombre archivo original: {filename_orig}")
    # logger.info(f"[Avatar] Nombre archivo generado: {filename}")
    # logger.info(f"[Avatar] Ruta completa de guardado: {filepath}")
    # logger.info(f"[Avatar] Ruta absoluta de guardado: {os.path.abspath(filepath)}")

    try:
        file.save(filepath)
        # logger.info(f"[Avatar] Avatar guardado exitosamente")
    except Exception as e:
        logger.error(f"[Avatar] Error guardando archivo: {e}")
        return jsonify(
            {"success": False, "error": f"Error al guardar archivo: {str(e)}"}
        ), 500

    # LOG 5: Después de guardar
    logger.info(
        f"[Avatar] Archivo guardado. ¿Existe? {os.path.exists(os.path.abspath(filepath))}"
    )
    if os.path.exists(os.path.abspath(filepath)):
        logger.info(
            f"[Avatar] Tamaño del archivo: {os.path.getsize(os.path.abspath(filepath))} bytes"
        )
        logger.info(
            f"[Avatar] Permisos del archivo: {oct(os.stat(os.path.abspath(filepath)).st_mode)[-3:]}"
        )
    else:
        logger.error(f"[Avatar] ❌ El archivo NO se guardó correctamente")

    # LOG 6: URL generada
    avatar_url = f"/static/uploads/avatars/{filename}"
    # logger.info(f"[Avatar] URL generada: {avatar_url}")
    # logger.info(f"[Avatar] ===== FIN SUBIDA AVATAR =====\n")

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

