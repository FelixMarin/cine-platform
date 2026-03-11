"""
Script de inicialización de la base de datos
Crea las tablas si no existen
"""

import sys
import os

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
)

from src.infrastructure.database.connection import get_engine
from src.infrastructure.models.catalog import Base


def init_db():
    """Inicializa la base de datos creando las tablas"""
    from src.infrastructure.config.settings import settings

    print(
        f"Conectando a: {settings.CINE_DB_HOST}:{settings.CINE_DB_PORT}/{settings.CINE_DB_NAME}"
    )

    engine = get_engine()

    print("Creando tablas...")
    Base.metadata.create_all(engine)

    print("Tablas creadas correctamente:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")

    engine.dispose()


if __name__ == "__main__":
    init_db()
