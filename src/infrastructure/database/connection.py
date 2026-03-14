"""
Configuración de conexión a la base de datos PostgreSQL
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from src.infrastructure.config.settings import settings

_engine = None
_SessionLocal = None


def get_engine():
    """Obtiene o crea el motor de base de datos"""
    global _engine
    if _engine is None:
        database_url = settings.CINE_DATABASE_URL
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=settings.CINE_DB_POOL_SIZE,
            max_overflow=settings.CINE_DB_MAX_OVERFLOW,
            pool_timeout=settings.CINE_DB_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_maker():
    """Obtiene el creador de sesiones"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


def get_db_session() -> Session:
    """Obtiene una sesión de base de datos"""
    SessionLocal = get_session_maker()
    return SessionLocal()


def get_db():
    """Generador de sesiones para inyección de dependencias"""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()
