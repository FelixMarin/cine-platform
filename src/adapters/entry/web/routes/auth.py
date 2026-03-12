"""
Adaptador de entrada - Rutas de autenticación
Blueprint para /api/auth y login
"""

from flask import (
    Blueprint,
    jsonify,
    request,
    session,
    render_template,
    redirect,
    url_for,
)
from src.core.services.role_service import RoleService
from src.core.services.UserSyncService import UserSyncService
from src.adapters.outgoing.repositories.cine.app_user_repository import (
    AppUserRepository,
)
import os
import base64
import json
import secrets
import hashlib
import requests
from urllib.parse import urlencode

from src.core.use_cases.auth import LoginUseCase, LogoutUseCase
from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.adapters.config.dependencies import get_oauth_service, get_auth_service

from src.infrastructure.logging import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

auth_bp = Blueprint("auth", __name__)

# Blueprint para la página principal (sin prefijo)
main_page_bp = Blueprint("main_page", __name__)


@main_page_bp.route("/status")
def status():
    """Estado de la API"""
    return jsonify({"status": "ok"})


@main_page_bp.route("/")
@require_auth
def index():
    """Página principal del catálogo"""
    return render_template("index.html")


@main_page_bp.route("/favicon.ico")
def favicon():
    """Favicon"""
    from flask import send_from_directory

    static_dir = os.path.join(os.getcwd(), "static")
    return send_from_directory(
        static_dir, "favicon.ico", mimetype="image/vnd.microsoft.icon"
    )


# Casos de uso inyectados
_login_use_case = None
_logout_use_case = None
_app_user_repo = None
_user_sync_service = None


def init_user_sync():
    """Inicializa el servicio de sincronización de usuarios"""
    global _app_user_repo, _user_sync_service
    if _app_user_repo is None:
        _app_user_repo = AppUserRepository()
    if _user_sync_service is None:
        _user_sync_service = UserSyncService(_app_user_repo)
    logger.info("[Auth] UserSyncService inicializado")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    """Página de login - GET"""
    # Obtener client_id de la URL (viene de la aplicación que redirige)
    client_id = request.args.get("client_id")

    if not client_id:
        # Si no viene, intentar de la sesión
        client_id = session.get("client_id")

    if not client_id:
        # Fallback a variable de entorno
        client_id = os.environ.get("OAUTH2_CLIENT_ID", "cine-platform")

    # Guardar en sesión para usarlo después
    session["client_id"] = client_id

    logger.info(f"[LOGIN_PAGE] Mostrando login para aplicación: {client_id}")

    # Verificar si hay parámetros OAuth2
    code_challenge = request.args.get("code_challenge")
    oauth_state = request.args.get("state")

    if code_challenge:
        # Si venimos de OAuth, guardar code_verifier
        code_verifier = _generate_code_verifier()
        session["oauth_code_verifier"] = code_verifier
        session["oauth_state"] = oauth_state
        logger.info(f"[LOGIN_PAGE] Code verifier guardado para OAuth")

    return render_template(
        "login.html",
        client_id=client_id,
        oauth2_url=os.environ.get("PUBLIC_OAUTH2_URL", "http://localhost:8080"),
        redirect_uri=os.environ.get(
            "PUBLIC_REDIRECT_URI", "http://localhost:5000/oauth/callback"
        ),
        code_challenge=code_challenge,
        state=oauth_state,
    )


@auth_bp.route("/login", methods=["POST"])
def login_post():
    """Procesar formulario de login - POST"""
    username = request.form.get("username")
    password = request.form.get("password")

    # Obtener client_id del formulario (campo hidden)
    client_id = request.form.get("client_id")

    # Obtener parámetros OAuth2 si existen
    code_challenge = request.form.get("code_challenge")
    oauth_state = request.form.get("state")

    # Validaciones
    if not username or not password:
        return render_template(
            "login.html",
            error="Usuario y contraseña requeridos",
            client_id=client_id or session.get("client_id"),
        )

    if not client_id:
        client_id = session.get("client_id")
        if not client_id:
            logger.error("[LOGIN] No se pudo determinar el client_id")
            return render_template(
                "login.html", error="Error: Aplicación no identificada"
            )

    logger.info(
        f"[LOGIN] Intento de login para usuario: {username} en aplicación: {client_id}"
    )

    # Hacer petición al servidor OAuth2
    oauth2_url = os.environ.get("OAUTH2_URL", "http://oauth2-server:8080")

    try:
        # Enviar credenciales al servidor OAuth2
        response = requests.post(
            f"{oauth2_url}/login",
            data={
                "username": username,
                "password": password,
                "client_id": client_id,  # ← Esto es CRÍTICO para multi-tenancy
            },
            allow_redirects=False,
            timeout=10,
        )

        if response.status_code == 302:
            # Login exitoso en OAuth2 server
            logger.info(
                f"[LOGIN] Login exitoso en OAuth2 server para {username} en {client_id}"
            )

            # Establecer sesión local
            session["logged_in"] = True
            session["username"] = username
            session["client_id"] = client_id
            
            # Sincronizar usuario con app_users
            try:
                if _user_sync_service is None:
                    init_user_sync()
                
                # Buscar el usuario por email o username
                oauth_user_data = {
                    "id": None,  # No tenemos el ID de OAuth, usar el email como identificador
                    "username": username,
                    "email": f"{username}@{client_id}.local",  # Generar email temporal
                    "display_name": username,
                }
                
                app_user = _user_sync_service.sync_user(oauth_user_data)
                
                session["app_user_id"] = app_user["id"]
                session["user_id"] = app_user["id"]
                session["display_name"] = app_user.get("display_name")
                
                logger.info(f"[LOGIN] Usuario sincronizado en app_users: ID {app_user['id']}")
            except Exception as sync_error:
                logger.error(f"[LOGIN] Error sincronizando usuario: {sync_error}")
                session["app_user_id"] = None
                session["user_id"] = None

            # Si hay code_challenge, redirigir al flujo OAuth2
            if code_challenge:
                return _complete_oauth_flow(code_challenge, oauth_state)

            # Redirigir a página principal
            return redirect(url_for("main_page.index"))

        else:
            # Login falló
            logger.warning(
                f"[LOGIN] Credenciales incorrectas para {username} en {client_id}"
            )
            return render_template(
                "login.html",
                error="Credenciales incorrectas para esta aplicación",
                client_id=client_id,
            )

    except requests.exceptions.ConnectionError:
        logger.error(f"[LOGIN] Error de conexión con servidor OAuth2 en {oauth2_url}")
        return render_template(
            "login.html",
            error="Error de conexión con servidor de autenticación",
            client_id=client_id,
        )
    except Exception as e:
        logger.error(f"[LOGIN] Error inesperado: {e}")
        return render_template(
            "login.html", error="Error interno del servidor", client_id=client_id
        )


def init_auth_routes(
    login_use_case: LoginUseCase = None, logout_use_case: LogoutUseCase = None
):
    """Inicializa los casos de uso para las rutas de autenticación"""
    global _login_use_case, _logout_use_case
    _login_use_case = login_use_case
    _logout_use_case = logout_use_case

    try:
        init_user_sync()
    except Exception as e:
        logger.error(f"[Auth] Error inicializando UserSyncService: {e}")


def get_user_id():
    """Obtiene el ID del usuario de la sesión"""
    return session.get("user_id", 0)


def is_logged_in():
    """Verifica si el usuario está logueado"""
    return session.get("logged_in", False)


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """Endpoint de login - Versión con RoleService"""
    global _login_use_case

    logger.info(f"[API LOGIN] Intento de login - LoginUseCase: {_login_use_case}")

    if _login_use_case is None:
        logger.error("[API LOGIN] LoginUseCase no inicializado")
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        data = request.get_json()

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email y password son requeridos"}), 400

        logger.info(f"[API LOGIN] Email: {email}")

        success, user_data = _login_use_case.execute(email, password)

        if success:
            # 🔴 CONVERTIR user_data A FORMATO user_info
            user_info = {
                "sub": str(user_data.get("id")),
                "email": user_data.get("email"),
                "preferred_username": user_data.get("username"),
                "name": user_data.get("username"),
                "roles": user_data.get("roles", []),
                "role": user_data.get("role"),
            }

            # 🔴 USAR ROLE SERVICE PARA PROCESAR ROLES
            user_session = RoleService.process_user_data(user_info)

            # Guardar en sesión
            session.permanent = True
            session["logged_in"] = True
            session.update(user_session)

            # Sincronizar usuario con base de datos de la app
            try:
                if _user_sync_service is None:
                    init_user_sync()

                oauth_user_data = {
                    "id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "roles": user_session.get("user_roles", []),
                    "display_name": user_data.get("full_name")
                    or user_data.get("username"),
                }

                logger.info(
                    f"[API LOGIN] Sincronizando usuario con app DB: {oauth_user_data}"
                )

                app_user = _user_sync_service.sync_user(oauth_user_data)

                session["app_user_id"] = app_user["id"]
                session["user_id"] = app_user["id"]  # Alias para compatibilidad
                session["display_name"] = app_user.get("display_name")
                session["avatar_url"] = app_user.get("avatar_url")
                session["privacy_level"] = app_user.get("privacy_level")

                logger.info(
                    f"[API LOGIN] Usuario sincronizado en app DB: ID {app_user['id']}"
                )

            except Exception as sync_error:
                logger.error(
                    f"[API LOGIN] Error sincronizando usuario en app DB: {sync_error}",
                    exc_info=True,
                )
                session["app_user_id"] = None
                session["display_name"] = session.get("username")
                session["avatar_url"] = None

            logger.info(
                f"[API LOGIN] Login exitoso para: {email}, rol: {session['user_role']}"
            )

            return jsonify({"success": True, "user": user_data})
        else:
            logger.warning(f"[API LOGIN] Credenciales incorrectas para: {email}")
            return jsonify({"success": False, "error": "Credenciales inválidas"}), 401

    except Exception as e:
        logger.error(f"[API LOGIN] Error: {e}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """Endpoint de logout"""
    global _logout_use_case

    if _logout_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        user_id = get_user_id()
        _logout_use_case.execute(user_id)

        # Limpiar sesión
        session.clear()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/auth/check", methods=["GET"])
def check_auth():
    """Verifica el estado de autenticación"""
    if is_logged_in():
        return jsonify(
            {
                "logged_in": True,
                "user_id": session.get("user_id"),
                "app_user_id": session.get("app_user_id"),
                "email": session.get("email"),
                "username": session.get("username"),
                "display_name": session.get("display_name"),
                "avatar_url": session.get("avatar_url"),
                "user_role": session.get("user_role"),
                "client_id": session.get("client_id"),
            }
        )
    else:
        return jsonify({"logged_in": False})


@auth_bp.route("/api/auth/session", methods=["GET"])
def get_session_info():
    """Devuelve información de la sesión actual (para depuración)"""
    return jsonify(
        {
            "logged_in": session.get("logged_in", False),
            "user_id": session.get("user_id"),
            "app_user_id": session.get("app_user_id"),
            "username": session.get("username"),
            "display_name": session.get("display_name"),
            "email": session.get("email"),
            "user_role": session.get("user_role"),
            "avatar_url": session.get("avatar_url"),
        }
    )


@auth_bp.route("/api/auth/token", methods=["POST"])
def verify_token():
    """Verifica un token de autenticación"""
    global _login_use_case

    if _login_use_case is None:
        return jsonify({"error": "Servicio no inicializado"}), 500

    try:
        data = request.get_json()
        token = data.get("token")

        if not token:
            return jsonify({"error": "Token es requerido"}), 400

        user_data = _login_use_case.verify_token(token)

        if user_data:
            return jsonify({"valid": True, "user": user_data})
        else:
            return jsonify({"valid": False}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================
#  ENDPOINTS PARA OAuth2 (BACKEND)
# ============================
@auth_bp.route("/api/auth/exchange-token", methods=["POST"])
def exchange_token():
    """Intercambia código por token - Versión con RoleService"""
    try:
        data = request.get_json()
        code = data.get("code")
        code_verifier = data.get("code_verifier")
        redirect_uri = data.get("redirect_uri")

        if not code or not code_verifier:
            return jsonify({"error": "Código y verifier requeridos"}), 400

        oauth2_url = os.environ.get("OAUTH2_URL", "http://oauth2-server:8080").rstrip(
            "/"
        )
        client_id = os.environ.get("OAUTH2_CLIENT_ID", "cine-platform")
        client_secret = os.environ.get("OAUTH2_CLIENT_SECRET", "cine-platform")

        # Basic Auth
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)

        token_response = requests.post(
            f"{oauth2_url}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=auth,
        )

        if token_response.status_code != 200:
            logger.error(f"[EXCHANGE_TOKEN] Error: {token_response.text}")
            return jsonify(
                {"error": "Error intercambiando código"}
            ), token_response.status_code

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        # Obtener userinfo para roles
        user_info = None
        try:
            userinfo_response = requests.get(
                f"{oauth2_url}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            logger.info(f"[EXCHANGE_TOKEN] 🔴 TOKEN {access_token}")
            if userinfo_response.status_code == 200:
                user_info = userinfo_response.json()
                logger.info(f"[EXCHANGE_TOKEN] Userinfo obtenido")
        except Exception as e:
            logger.warning(f"[EXCHANGE_TOKEN] Error obteniendo userinfo: {e}")

        # 🔴 USAR ROLE SERVICE PARA PROCESAR ROLES
        user_session = RoleService.process_user_data(user_info, access_token)

        # Guardar en sesión
        session.permanent = True
        session["logged_in"] = True
        session.update(user_session)
        session["client_id"] = client_id
        session["oauth_token"] = access_token
        session["oauth_refresh_token"] = token_data.get("refresh_token")

        # Sincronizar usuario con base de datos de la app
        if user_info:
            try:
                if _user_sync_service is None:
                    init_user_sync()

                # Extraer username del JWT: usar sub como fallback si no hay preferred_username
                # El JWT típico tiene: sub, email, name, preferred_username
                username = (
                    user_info.get("preferred_username")
                    or user_info.get("username")
                    or user_info.get("sub").split("@")[0]  # Usar parte antes de @ del email
                    if user_info.get("sub")
                    else None
                )
                
                # El email puede estar en "email" o en "sub" (si es email)
                email = user_info.get("email") or user_info.get("sub")
                
                # El display_name puede estar en "name" o en "preferred_username"
                display_name = user_info.get("name") or username
                
                oauth_user_data = {
                    "id": user_info.get("id") or user_info.get("sub"),
                    "username": username,
                    "email": email,
                    "roles": user_session.get("user_roles", []),
                    "display_name": display_name,
                }
                
                logger.info(f"[EXCHANGE_TOKEN] Datos OAuth extraídos: {oauth_user_data}")

                logger.info(f"[EXCHANGE_TOKEN] Sincronizando usuario con app DB")

                app_user = _user_sync_service.sync_user(oauth_user_data)

                session["app_user_id"] = app_user["id"]
                session["display_name"] = app_user.get("display_name")
                session["avatar_url"] = app_user.get("avatar_url")
                session["privacy_level"] = app_user.get("privacy_level")

                logger.info(
                    f"[EXCHANGE_TOKEN] Usuario sincronizado en app DB: ID {app_user['id']}"
                )

            except Exception as sync_error:
                logger.error(
                    f"[EXCHANGE_TOKEN] Error sincronizando usuario en app DB: {sync_error}"
                )
                session["app_user_id"] = None
                session["display_name"] = session.get("username")
                session["avatar_url"] = None

        logger.info(
            f"[EXCHANGE_TOKEN] Login OAuth2 exitoso para: {session['username']}, rol: {session['user_role']}"
        )

        return jsonify(token_data)

    except Exception as e:
        logger.error(f"[EXCHANGE_TOKEN] Error: {e}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/auth/refresh-token", methods=["POST"])
def refresh_token():
    """
    Refresca el token de acceso
    """
    try:
        data = request.get_json()
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            return jsonify({"error": "Refresh token requerido"}), 400

        # Obtener configuración
        oauth2_url = os.environ.get("OAUTH2_URL", "http://oauth2-server:8080").rstrip(
            "/"
        )
        client_id = os.environ.get("OAUTH2_CLIENT_ID", "cine-platform")
        client_secret = os.environ.get("OAUTH2_CLIENT_SECRET", "cine-platform")

        # Hacer petición de refresh
        refresh_response = requests.post(
            f"{oauth2_url}/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if refresh_response.status_code != 200:
            logger.error(f"[REFRESH_TOKEN] Error: {refresh_response.text}")
            return jsonify(
                {"error": "Error refrescando token"}
            ), refresh_response.status_code

        token_data = refresh_response.json()

        # Actualizar sesión
        session["oauth_token"] = token_data.get("access_token")
        if token_data.get("refresh_token"):
            session["oauth_refresh_token"] = token_data.get("refresh_token")

        return jsonify(token_data)

    except Exception as e:
        logger.error(f"[REFRESH_TOKEN] Error: {e}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/auth/userinfo", methods=["GET"])
def userinfo():
    """
    Obtiene información del usuario desde el OAuth2 server
    """
    try:
        token = session.get("oauth_token")

        if not token:
            return jsonify({"error": "No autenticado"}), 401

        oauth2_url = os.environ.get("OAUTH2_URL", "http://oauth2-server:8080").rstrip(
            "/"
        )

        # Hacer petición a userinfo
        userinfo_response = requests.get(
            f"{oauth2_url}/userinfo", headers={"Authorization": f"Bearer {token}"}
        )

        if userinfo_response.status_code != 200:
            return jsonify(
                {"error": "Error obteniendo información"}
            ), userinfo_response.status_code

        userinfo_data = userinfo_response.json()

        # Intentar obtener roles del token almacenado usando RoleService
        roles = []
        if token:
            try:
                import jwt

                jwt_payload = jwt.decode(token, options={"verify_signature": False})
                roles = jwt_payload.get("roles", [])
            except:
                pass

        # Añadir roles a la respuesta si los tenemos
        if roles:
            userinfo_data["roles"] = roles

        return jsonify(userinfo_data)

    except Exception as e:
        logger.error(f"[USERINFO] Error: {e}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/auth/revoke-token", methods=["POST"])
def revoke_token():
    """
    Revoca un token en el OAuth2 server
    """
    try:
        data = request.get_json()
        token = data.get("token")

        if not token:
            return jsonify({"error": "Token requerido"}), 400

        oauth2_url = os.environ.get("OAUTH2_URL", "http://oauth2-server:8080").rstrip(
            "/"
        )

        # Hacer petición de revocación
        revoke_response = requests.post(
            f"{oauth2_url}/oauth2/revoke", data={"token": token}
        )

        # Limpiar sesión independientemente del resultado
        session.pop("oauth_token", None)
        session.pop("oauth_refresh_token", None)

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"[REVOKE_TOKEN] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
#  RUTAS DE PÁGINAS HTML (sin cambios)
# ============================


@auth_bp.route("/api/auth/oauth2/start", methods=["POST"])
def start_oauth2_flow():
    """
    Inicia el flujo OAuth2. Genera code_verifier, guarda en sesión y devuelve la URL de autorización.
    El frontend debe redirigir a esta URL.
    """
    try:
        # Verificar que no hay sesión activa (para evitar accesos no autorizados)
        logger.info(f"[OAUTH_START] Request cookies: {dict(request.cookies)}")
        logger.info(
            f"[OAUTH_START] Session keys: {list(session.keys()) if session else 'No session'}"
        )
        logger.info(f"[OAUTH_START] Is logged in: {is_logged_in()}")

        # Si ya hay una sesión activa, no permitir iniciar OAuth2
        if is_logged_in():
            logger.warning(
                f"[OAUTH_START] Usuario ya logueado, redirigiendo a página principal"
            )
            return jsonify(
                {"success": False, "error": "Ya hay una sesión activa", "redirect": "/"}
            )

        # Generar code_verifier y code_challenge
        code_verifier = _generate_code_verifier()
        code_challenge = _generate_code_challenge(code_verifier)

        # Limpiar cualquier code_verifier anterior y guardar el nuevo
        session.pop("oauth_code_verifier", None)
        session.pop("oauth_state", None)
        session["oauth_code_verifier"] = code_verifier

        # Generar state aleatorio
        state = secrets.token_urlsafe(16)
        session["oauth_state"] = state

        # Obtener configuración
        oauth2_url = os.environ.get(
            "PUBLIC_OAUTH2_URL", "http://localhost:8080"
        ).rstrip("/")
        client_id = os.environ.get("OAUTH2_CLIENT_ID", "default-user")
        redirect_uri = os.environ.get(
            "PUBLIC_REDIRECT_URI", "http://localhost:5000/oauth/callback"
        ).rstrip("/")

        # Construir URL de autorización
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile read write",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "prompt": "login",
        }

        auth_url = f"{oauth2_url}/oauth2/authorize?{urlencode(params)}"
        logger.info(f"[OAUTH_START] URL de autorización generada: {auth_url[:100]}...")

        return jsonify({"success": True, "authorization_url": auth_url})

    except Exception as e:
        logger.error(f"[OAUTH_START] Error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _complete_oauth_flow(code_challenge: str, state: str = None):
    """
    Completa el flujo OAuth2 después del login.
    Genera el code_verifier, lo guarda en sesión y redirige al servidor OAuth2.
    """
    try:
        logger.info(
            f"[OAUTH_FLOW] Iniciando flujo OAuth2 con code_challenge: {code_challenge[:30]}..."
        )

        code_verifier = session.get("oauth_code_verifier")
        if not code_verifier:
            code_verifier = _generate_code_verifier()
            session["oauth_code_verifier"] = code_verifier
            logger.info(f"[OAUTH_FLOW] Code verifier generado: {code_verifier[:30]}...")

        oauth2_url = os.environ.get(
            "PUBLIC_OAUTH2_URL", "http://localhost:8080"
        ).rstrip("/")
        # 🔴 USAR CLIENT_ID DE SESIÓN
        client_id = session.get("client_id") or os.environ.get(
            "OAUTH2_CLIENT_ID", "cine-platform"
        )
        redirect_uri = os.environ.get(
            "PUBLIC_REDIRECT_URI", "http://localhost:5000/oauth/callback"
        ).rstrip("/")

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile read write",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "login",
        }
        if state:
            params["state"] = state

        auth_url = f"{oauth2_url}/oauth2/authorize?{urlencode(params)}"
        logger.info(f"[OAUTH_FLOW] Redirigiendo a: {auth_url}")

        return redirect(auth_url)

    except Exception as e:
        logger.error(f"[OAUTH_FLOW] Error: {e}")
        return render_template(
            "login.html", error=f"Error al completar OAuth: {str(e)}"
        )


def _generate_code_verifier() -> str:
    """Genera un code_verifier aleatorio (43-128 caracteres)"""
    random_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")
    return verifier


def _generate_code_challenge(verifier: str) -> str:
    """Genera un code_challenge a partir del code_verifier usando SHA-256"""
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return challenge


@auth_bp.route("/auth/callback", methods=["POST"])
def oauth_callback():
    """
    Callback de OAuth2 - Intercambia código por token - Versión con RoleService
    """
    try:
        data = request.get_json()
        code = data.get("code")
        code_verifier = data.get("code_verifier")

        if not code or not code_verifier:
            logger.warning("[OAUTH_CALLBACK] Código o verifier faltante")
            return jsonify(
                {"success": False, "error": "Código o verifier faltante"}
            ), 400

        logger.info("[OAUTH_CALLBACK] Intercambiando código por token")

        oauth_service = get_oauth_service()

        if not oauth_service:
            logger.error("[OAUTH_CALLBACK] Servicio OAuth no disponible")
            return jsonify(
                {"success": False, "error": "Servicio OAuth no disponible"}
            ), 500

        success, token_data = oauth_service.exchange_code_for_token(code, code_verifier)

        if not success:
            logger.error(f"[OAUTH_CALLBACK] Error intercambiando código: {token_data}")
            return jsonify(
                {
                    "success": False,
                    "error": token_data.get("error", "Error desconocido"),
                }
            ), 400

        access_token = token_data.get("access_token")
        user_info = oauth_service.get_userinfo(access_token)

        # 🔴 USAR ROLE SERVICE PARA PROCESAR ROLES
        user_session = RoleService.process_user_data(user_info, access_token)

        # Guardar en sesión
        session.permanent = True
        session["logged_in"] = True
        session.update(user_session)
        session["oauth_token"] = access_token
        session["oauth_refresh_token"] = token_data.get("refresh_token")
        session["oauth_expires_at"] = token_data.get("expires_at")

        # Sincronizar usuario con base de datos de la app
        try:
            if _user_sync_service is None:
                init_user_sync()

            # Extraer username del JWT: usar sub como fallback si no hay preferred_username
            username = (
                user_info.get("preferred_username")
                or user_info.get("username")
                or user_info.get("sub").split("@")[0]  # Usar parte antes de @ del email
                if user_info.get("sub")
                else None
            )
            
            # El email puede estar en "email" o en "sub" (si es email)
            email = user_info.get("email") or user_info.get("sub")
            
            # El display_name puede estar en "name" o en "preferred_username"
            display_name = user_info.get("name") or username
            
            oauth_user_data = {
                "id": user_info.get("id") or user_info.get("sub"),
                "username": username,
                "email": email,
                "roles": user_session.get("user_roles", []),
                "display_name": display_name,
            }
            
            logger.info(f"[OAUTH_CALLBACK] Datos OAuth extraídos: {oauth_user_data}")
            logger.info(f"[OAUTH_CALLBACK] Sincronizando usuario con app DB")

            app_user = _user_sync_service.sync_user(oauth_user_data)

            session["app_user_id"] = app_user["id"]
            session["display_name"] = app_user.get("display_name")
            session["avatar_url"] = app_user.get("avatar_url")
            session["privacy_level"] = app_user.get("privacy_level")

            logger.info(
                f"[OAUTH_CALLBACK] Usuario sincronizado en app DB: ID {app_user['id']}"
            )

        except Exception as sync_error:
            logger.error(
                f"[OAUTH_CALLBACK] Error sincronizando usuario en app DB: {sync_error}"
            )
            session["app_user_id"] = None
            session["display_name"] = session.get("username")
            session["avatar_url"] = None

        logger.info(
            f"[OAUTH_CALLBACK] Login OAuth2 exitoso para: {session.get('username')}, rol: {session.get('user_role')}"
        )

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/oauth/callback", methods=["GET"])
def oauth_callback_redirect():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "Código faltante", 400

    # Solo redirigir al frontend
    frontend_url = os.environ.get("PUBLIC_URL", "http://localhost:5000")
    return redirect(f"{frontend_url}/login?code={code}&state={state}")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout_page():
    """Página de logout"""
    from flask import current_app, make_response

    logger.info(f"[LOGOUT] Cookies recibidas: {dict(request.cookies)}")

    try:
        oauth_token = session.get("oauth_token")
        if oauth_token:
            oauth_service = get_oauth_service()
            if oauth_service:
                oauth_service.revoke_token(oauth_token)
                logger.info("[LOGOUT] Token revocado en servidor OAuth2")
    except Exception as e:
        logger.warning(f"[LOGOUT] Error revocando token: {e}")

    logger.info("[LOGOUT] Usuario cerró sesión - limpiando datos")

    session_keys = list(session.keys())
    logger.info(f"[LOGOUT] Keys en sesión antes de limpiar: {session_keys}")
    session.clear()

    session.modified = True

    response = make_response(redirect("/login"))

    base_options = {
        "httponly": True,
        "samesite": "Lax",
    }

    if current_app.config.get("SESSION_COOKIE_SECURE", False):
        base_options["secure"] = True

    response.set_cookie("session", "", max_age=0, path="/", **base_options)

    try:
        cookie_domain = current_app.config.get("SESSION_COOKIE_DOMAIN")
        cookie_path = current_app.config.get("SESSION_COOKIE_PATH", "/")
        logger.info(f"[LOGOUT] Cookie domain: {cookie_domain}, path: {cookie_path}")
        if cookie_domain:
            response.set_cookie(
                "session", "", max_age=0, domain=cookie_domain, **base_options
            )
    except Exception as e:
        logger.warning(f"[LOGOUT] Error eliminando cookie de dominio: {e}")

    logger.info(
        "[LOGOUT] Session cleared, all cookies set to expire, redirecting to login"
    )
    return response


@auth_bp.route("/logout-check", methods=["GET"])
def logout_check():
    """Endpoint para verificar el estado del logout"""
    logger.info(f"[LOGOUT_CHECK] Cookies: {dict(request.cookies)}")
    logger.info(f"[LOGOUT_CHECK] Session keys: {list(session.keys())}")
    logger.info(f"[LOGOUT_CHECK] Is logged in: {is_logged_in()}")
    return jsonify(
        {
            "logged_in": is_logged_in(),
            "session_keys": list(session.keys()),
            "cookies": list(request.cookies.keys()),
        }
    )
