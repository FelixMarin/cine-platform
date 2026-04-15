import logging
from typing import Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.domain.ports.out.repositories.IAppUserRepository import IAppUserRepository
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


class AppUserRepository(IAppUserRepository):
    """Implementación con SQLAlchemy para cine_app_db"""

    def __init__(self):
        logger.info(
            f"[AppUserRepository] Conectando a {settings.CINE_DB_HOST}/{settings.CINE_DB_NAME}"
        )
        self.engine = create_engine(
            settings.CINE_DATABASE_URL,
            pool_size=settings.CINE_DB_POOL_SIZE,
            max_overflow=settings.CINE_DB_MAX_OVERFLOW,
            pool_timeout=settings.CINE_DB_POOL_TIMEOUT,
            echo=False,
        )
        self.Session = sessionmaker(bind=self.engine)

    def get_by_id(self, app_user_id: int) -> Optional[Dict]:
        """Obtiene perfil por ID interno"""
        with self.Session() as session:
            result = session.execute(
                text("""
                    SELECT id, oauth_user_id, username, email, display_name, 
                           avatar_url, bio, privacy_level, settings,
                           created_at, last_active
                    FROM app_users 
                    WHERE id = :id
                """),
                {"id": app_user_id},
            ).first()

            if result:
                return {
                    "id": result[0],
                    "oauth_user_id": result[1],
                    "username": result[2],
                    "email": result[3],
                    "display_name": result[4],
                    "avatar_url": result[5],
                    "bio": result[6],
                    "privacy_level": result[7],
                    "settings": result[8],
                    "created_at": result[9],
                    "last_active": result[10],
                }
            return None

    def get_by_oauth_id(self, oauth_user_id: int) -> Optional[Dict]:
        """Obtiene perfil por ID de OAuth2"""
        with self.Session() as session:
            result = session.execute(
                text("""
                    SELECT id, oauth_user_id, username, email, display_name, 
                           avatar_url, bio, privacy_level, settings,
                           created_at, last_active
                    FROM app_users 
                    WHERE oauth_user_id = :oauth_user_id
                """),
                {"oauth_user_id": oauth_user_id},
            ).first()

            if result:
                return {
                    "id": result[0],
                    "oauth_user_id": result[1],
                    "username": result[2],
                    "email": result[3],
                    "display_name": result[4],
                    "avatar_url": result[5],
                    "bio": result[6],
                    "privacy_level": result[7],
                    "settings": result[8],
                    "created_at": result[9],
                    "last_active": result[10],
                }
            return None

    def get_by_username(self, username: str) -> Optional[Dict]:
        """Obtiene perfil por nombre de usuario"""
        with self.Session() as session:
            result = session.execute(
                text("SELECT * FROM app_users WHERE username = :username"),
                {"username": username},
            ).first()
            return dict(result._mapping) if result else None

    def get_by_email(self, email: str) -> Optional[Dict]:
        """Obtiene perfil por email"""
        with self.Session() as session:
            result = session.execute(
                text("SELECT * FROM app_users WHERE email = :email"), {"email": email}
            ).first()
            return dict(result._mapping) if result else None

    def user_exists(self, oauth_user_id: int) -> bool:
        """Verifica si ya existe perfil para este usuario OAuth2"""
        with self.Session() as session:
            result = session.execute(
                text("SELECT 1 FROM app_users WHERE oauth_user_id = :oauth_user_id"),
                {"oauth_user_id": oauth_user_id},
            ).first()
            return result is not None

    def create_from_oauth(self, oauth_data: Dict) -> int:
        """
        Crea perfil desde datos de OAuth2
        """
        with self.Session() as session:
            existing = self.get_by_oauth_id(oauth_data["id"])
            if existing:
                logger.warning(
                    f"[AppUserRepository] Usuario OAuth2 {oauth_data['id']} ya existe, retornando ID existente"
                )
                return existing["id"]

            result = session.execute(
                text("""
                    INSERT INTO app_users 
                        (oauth_user_id, username, email, display_name, created_at, last_active)
                    VALUES 
                        (:oauth_user_id, :username, :email, :display_name, NOW(), NOW())
                    RETURNING id
                """),
                {
                    "oauth_user_id": oauth_data["id"],
                    "username": oauth_data["username"],
                    "email": oauth_data["email"],
                    "display_name": oauth_data.get(
                        "display_name", oauth_data["username"]
                    ),
                },
            )
            session.commit()

            new_id = result.scalar()
            logger.info(
                f"[AppUserRepository] Nuevo perfil creado para usuario OAuth2 {oauth_data['id']} (app_user_id: {new_id})"
            )

            try:
                session.execute(
                    text("""
                        INSERT INTO user_preferences (app_user_id, updated_at)
                        VALUES (:app_user_id, NOW())
                    """),
                    {"app_user_id": new_id},
                )
                session.commit()
            except Exception as e:
                logger.warning(
                    f"[AppUserRepository] No se pudieron crear preferencias: {e}"
                )

            return new_id

    def update_profile(self, app_user_id: int, data: Dict) -> bool:
        """
        Actualiza datos del perfil
        Solo permite actualizar campos específicos por seguridad
        """
        allowed_fields = [
            "display_name",
            "bio",
            "privacy_level",
            "avatar_url",
            "settings",
        ]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            logger.warning("[AppUserRepository] No hay campos válidos para actualizar")
            return False

        with self.Session() as session:
            set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
            update_data["id"] = app_user_id

            result = session.execute(
                text(f"UPDATE app_users SET {set_clause} WHERE id = :id"), update_data
            )
            session.commit()

            success = result.rowcount > 0
            if success:
                logger.info(
                    f"[AppUserRepository] Perfil {app_user_id} actualizado: {list(update_data.keys())}"
                )
            return success

    def update_last_active(self, app_user_id: int) -> None:
        """Actualiza última actividad del usuario"""
        with self.Session() as session:
            session.execute(
                text("UPDATE app_users SET last_active = NOW() WHERE id = :id"),
                {"id": app_user_id},
            )
            session.commit()
