"""
Servicio de sincronización de usuarios entre OAuth2 y Cine App DB
"""

import logging
from typing import Dict, Optional

from src.domain.ports.out.repositories.IAppUserRepository import IAppUserRepository

logger = logging.getLogger(__name__)


class UserSyncService:
    """
    Servicio que sincroniza usuarios entre OAuth2 y la base de datos de la aplicación

    Flujo:
    1. Recibe datos del usuario desde OAuth2 (id, username, email, roles)
    2. Busca si ya existe perfil en cine_app_db
    3. Si no existe, lo crea
    4. Si existe, actualiza last_active
    5. Retorna datos del perfil para la sesión
    """

    def __init__(self, app_user_repository: IAppUserRepository):
        """
        Inicializa el servicio con el repositorio de usuarios de la app

        Args:
            app_user_repository: Implementación de IAppUserRepository
        """
        self.repo = app_user_repository
        logger.info("[UserSyncService] Inicializado")

    def sync_user(self, oauth_user_data: Dict) -> Dict:
        """
        Sincroniza un usuario después de login OAuth2

        Args:
            oauth_user_data: Diccionario con datos del usuario desde OAuth2
                {
                    'id': 123,                    # ID en oauth2_db (obligatorio)
                    'username': 'admin',           # Nombre de usuario (obligatorio)
                    'email': 'admin@example.com',  # Email (obligatorio)
                    'roles': ['ROLE_ADMIN'],       # Lista de roles (opcional)
                    'display_name': 'Admin User'   # Nombre para mostrar (opcional)
                }

        Returns:
            Dict: Datos del perfil en cine_app_db
                {
                    'id': 1,
                    'oauth_user_id': 123,
                    'username': 'admin',
                    'email': 'admin@example.com',
                    'display_name': 'Admin User',
                    'avatar_url': None,
                    'bio': None,
                    'privacy_level': 'public',
                    'created_at': ...,
                    'last_active': ...
                }

        Raises:
            ValueError: Si faltan datos obligatorios
            Exception: Si hay error en la base de datos
        """
        required_fields = ["id", "username", "email"]
        for field in required_fields:
            if field not in oauth_user_data:
                error_msg = f"Campo obligatorio faltante: {field}"
                logger.error(f"[UserSyncService] {error_msg}")
                raise ValueError(error_msg)

        oauth_id = oauth_user_data["id"]
        logger.info(f"[UserSyncService] Sincronizando usuario OAuth2 ID: {oauth_id}")

        try:
            existing_user = self.repo.get_by_oauth_id(oauth_id)

            if existing_user:
                logger.info(
                    f"[UserSyncService] Usuario existente encontrado (app_user_id: {existing_user['id']})"
                )
                self.repo.update_last_active(existing_user["id"])

                return self.repo.get_by_id(existing_user["id"]) or existing_user

            logger.info("[UserSyncService] Usuario nuevo, creando perfil...")

            create_data = {
                "id": oauth_id,
                "username": oauth_user_data["username"],
                "email": oauth_user_data["email"],
                "display_name": oauth_user_data.get(
                    "display_name", oauth_user_data["username"]
                ),
            }

            new_user_id = self.repo.create_from_oauth(create_data)
            logger.info(f"[UserSyncService] Perfil creado con ID: {new_user_id}")

            new_user = self.repo.get_by_id(new_user_id)
            if not new_user:
                raise Exception("El perfil se creó pero no se pudo recuperar")

            return new_user

        except Exception as e:
            logger.error(f"[UserSyncService] Error sincronizando usuario: {str(e)}")
            raise

    def get_user_profile(self, app_user_id: int) -> Optional[Dict]:
        """
        Obtiene perfil de usuario por ID interno

        Args:
            app_user_id: ID del usuario en cine_app_db (acepta string o int)

        Returns:
            Dict con datos del perfil o None si no existe
        """
        try:
            # Convertir a int si es necesario
            if isinstance(app_user_id, str):
                try:
                    app_user_id = int(app_user_id)
                except ValueError:
                    logger.error(f"[UserSyncService] user_id inválido: {app_user_id}")
                    return None

            return self.repo.get_by_id(app_user_id)
        except Exception as e:
            logger.error(
                f"[UserSyncService] Error obteniendo perfil {app_user_id}: {str(e)}"
            )
            return None

    def get_user_by_oauth_id(self, oauth_user_id: int) -> Optional[Dict]:
        """
        Obtiene perfil por ID de OAuth2

        Args:
            oauth_user_id: ID del usuario en oauth2_db

        Returns:
            Dict con datos del perfil o None si no existe
        """
        try:
            return self.repo.get_by_oauth_id(oauth_user_id)
        except Exception as e:
            logger.error(
                f"[UserSyncService] Error obteniendo perfil por OAuth ID {oauth_user_id}: {str(e)}"
            )
            return None

    def update_user_profile(self, app_user_id: int, data: Dict) -> bool:
        """
        Actualiza datos del perfil (solo campos permitidos)

        Args:
            app_user_id: ID del usuario en cine_app_db
            data: Diccionario con campos a actualizar
                  (display_name, bio, privacy_level, avatar_url, settings)

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            user = self.repo.get_by_id(app_user_id)
            if not user:
                logger.warning(
                    f"[UserSyncService] Intento de actualizar usuario inexistente: {app_user_id}"
                )
                return False

            success = self.repo.update_profile(app_user_id, data)
            if success:
                logger.info(f"[UserSyncService] Perfil {app_user_id} actualizado")
            return success

        except Exception as e:
            logger.error(
                f"[UserSyncService] Error actualizando perfil {app_user_id}: {str(e)}"
            )
            return False
