#!/bin/bash

set -e

echo "======================================"
echo "  🧪 Ejecutando tests con pytest"
echo "======================================"

# Eliminar archivo problemático si existe
if [ -f "test_profiles.py" ]; then
    echo "⚠️  Eliminando test_profiles.py conflictivo"
    mv test_profiles.py test_profiles.py.bak
fi

# Ejecutar tests
pytest tests/ -v --maxfail=1 --disable-warnings

echo "✔ Tests completados correctamente"

echo "======================================"
echo "  📊 Ejecutando coverage"
echo "======================================"

# Ejecutar coverage con opción para omitir archivos temporales
coverage run --omit="tests/templates/*" -m pytest tests/
coverage report -m --omit="tests/templates/*"
coverage html --omit="tests/templates/*"

echo "✔ Coverage generado correctamente"
echo "📁 Reporte HTML: htmlcov/index.html"

# Restaurar archivo si existe backup
if [ -f "test_profiles.py.bak" ]; then
    mv test_profiles.py.bak test_profiles.py
fi