#!/bin/bash

# Limpiar módulos mockeados de ejecuciones anteriores
unset PYTHONPATH
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

echo "======================================"
echo "  🧪 Ejecutando Tests de Cine Platform"
echo "======================================"

python -m unittest discover -s tests -p "test_*.py"

echo "======================================"
echo "  🧪 Ejecutando Tests de Cine Platform"
echo "======================================"

# Ejecutar descubrimiento de tests
python3 -m unittest discover -s tests -p "test_*.py" -v

echo "======================================"
