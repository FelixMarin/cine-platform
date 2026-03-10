#!/bin/bash
echo "🚀 Ejecutando migraciones..."
docker compose run --rm flyway
echo "✅ Migraciones completadas"
