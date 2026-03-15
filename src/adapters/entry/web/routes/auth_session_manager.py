"""
Servicio de gestión de sesión de usuario

Maneja las operaciones de sesión de usuario.
"""

import logging
from flask import session

logger = logging.getLogger(__name__)


class SessionManager:
    """Gestiona las operaciones de sesión de usuario"""

    @staticmethod
    def get_user_id():
        """Obtiene el ID del usuario de la sesión"""
        return session.get("user_id", 0)

    @staticmethod
    def is_logged_in():
        """Verifica si el usuario está logueado"""
        return session.get("logged_in", False)

    @staticmethod
    def create_user_session(user_session_data: dict):
        """
        Crea una sesión de usuario con los datos proporcionados.

        Args:
            user_session_data: Diccionario con datos del usuario
        """
        session.permanent = True
        session["logged_in"] = True
        session.update(user_session_data)

    @staticmethod
    def clear_session():
        """Limpia la sesión del usuario"""
        session.clear()

    @staticmethod
    def get_session_info() -> dict:
        """
        Obtiene información de la sesión actual.

        Returns:
            Diccionario con información de la sesión
        """
        return {
            "logged_in": session.get("logged_in", False),
            "user_id": session.get("user_id"),
            "app_user_id": session.get("app_user_id"),
            "username": session.get("username"),
            "display_name": session.get("display_name"),
            "email": session.get("email"),
            "user_role": session.get("user_role"),
            "avatar_url": session.get("avatar_url"),
            "client_id": session.get("client_id"),
        }

    @staticmethod
    def get_auth_check_info() -> dict:
        """
        Obtiene información para verificación de autenticación.

        Returns:
            Diccionario con información de autenticación
        """
        if SessionManager.is_logged_in():
            return {
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
        return {"logged_in": False}
