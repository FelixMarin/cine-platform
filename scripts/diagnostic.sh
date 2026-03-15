#!/bin/bash
# diagnostic.sh

echo "=== DIAGNÓSTICO DE RENDIMIENTO ==="

# 1. Verificar conexiones activas a BD
docker exec cine-postgres-prod psql -U cine_app_user -d cine_app_db -c "
SELECT count(*) as total_connections,
       count(*) filter (where state = 'active') as active,
       count(*) filter (where state = 'idle') as idle
FROM pg_stat_activity 
WHERE datname = 'cine_app_db';"

# 2. Verificar queries lentas
docker exec cine-postgres-prod psql -U cine_app_user -d cine_app_db -c "
SELECT query, 
       calls,
       total_time / 1000 as total_seconds,
       mean_time / 1000 as mean_seconds
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 5;"

# 3. Logs de la app con timestamps
docker logs cine-platform-prod --tail 50 | grep -E "thumbnail|time"