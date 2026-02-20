# modules/routes/auth.py
"""
Blueprint de autenticación: /login, /logout
"""
import os
import jwt
from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_wtf.csrf import generate_csrf
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

auth_bp = Blueprint('auth', __name__)

# Servicio inyectado desde fuera
auth_service = None


def init_auth_service(service):
    """Inicializa el servicio de autenticación"""
    global auth_service
    auth_service = service


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Generar token CSRF y guardarlo en sesión
        token = generate_csrf()
        session['csrf_token'] = token
        return render_template("login.html", csrf_token=token)

    # POST request - Validar CSRF token
    csrf_token = request.form.get('csrf_token')
    session_token = session.get('csrf_token')
    
    if not csrf_token or not session_token or csrf_token != session_token:
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Token de seguridad inválido", csrf_token=new_token), 400

    session.pop('csrf_token', None)

    username = request.form.get('email')
    password = request.form.get('password')

    if not username or not password:
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Usuario y contraseña requeridos", csrf_token=new_token), 400

    # Intentar login con el servicio OAuth
    success, info = auth_service.login(username, password)

    if not success:
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Credenciales incorrectas", csrf_token=new_token), 401

    # Login exitoso - procesar token JWT
    token = auth_service.token

    # Decodificar payload manualmente (debug)
    try:
        import base64
        import json
        parts = token.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload_json = base64.b64decode(payload_b64).decode('utf-8')
            payload = json.loads(payload_json)
    except Exception as e:
        logger.error(f"❌ Error decodificando payload: {e}")

    # Ver token sin verificar
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        logger.info(f"🔍 Token analizado sin verificar: {unverified.get('user_name')}")
    except Exception as e:
        logger.error(f"❌ Error decodificando token: {e}")
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error=f"Token inválido: {type(e).__name__}", csrf_token=new_token), 400

    try:
        import os
        decoded = jwt.decode(
            token,
            key=os.environ.get('JWT_SECRET_KEY'),
            algorithms=['HS256'],
            audience=[os.environ.get('JWT_AUDIENCE')],
            options={"verify_signature": True}
        )
        logger.info("✅ Token verificado correctamente")

        # Establecer sesión de usuario
        session['logged_in'] = True
        session['user_email'] = decoded.get("user_name", username)
        session.permanent = True

        authorities = decoded.get("authorities", [])
        session['user_role'] = "admin" if "ROLE_ADMIN" in authorities else "user"

        logger.info(f"✅ Usuario autenticado: {session['user_email']} (rol: {session['user_role']})")

        return redirect(url_for('streaming.index'))

    except jwt.ExpiredSignatureError:
        logger.error("❌ Token expirado")
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Sesión expirada", csrf_token=new_token), 400
    except jwt.InvalidAudienceError as e:
        logger.error(f"❌ Audience incorrecto: {e}")
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Error de autenticación", csrf_token=new_token), 400
    except jwt.InvalidSignatureError:
        logger.error("❌ Firma incorrecta")
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Error de autenticación", csrf_token=new_token), 400
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ Token inválido: {type(e).__name__}: {e}")
        new_token = generate_csrf()
        session['csrf_token'] = new_token
        return render_template("login.html", error="Error de autenticación", csrf_token=new_token), 400


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
