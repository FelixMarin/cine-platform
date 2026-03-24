"""
Script de inicialización de la base de datos
Crea las tablas si no existen
"""

import sys
import os

# Añadir el directorio raíz del proyecto al PYTHONPATH
# Asumiendo que este script está en /scripts/init_catalog_db.py
# y la raíz del proyecto es / (con src/, config/, etc.)
current_dir = os.path.dirname(os.path.abspath(__file__))  # scripts/
project_root = os.path.dirname(current_dir)  # Raíz del proyecto (cine-platform/)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"✅ Añadido {project_root} al PYTHONPATH")

# Ahora sí podemos importar desde src
from src.infrastructure.database.connection import get_engine
from src.infrastructure.models.catalog import Base
from src.infrastructure.models.optimization_history import OptimizationHistory
from src.infrastructure.config.settings import settings



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

