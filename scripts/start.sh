#!/bin/bash

# Script de inicio para cine-platform en producción
# Ubicación: ./scripts/start.sh
# Uso: ./scripts/start.sh [opciones]

set -e

# ============================================
# CONFIGURACIÓN
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
LOG_FILE="${PROJECT_DIR}/logs/start-$(date +%Y%m%d-%H%M%S).log"
COMPOSE_CMD="docker-compose -f ${COMPOSE_FILE}"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# FUNCIONES
# ============================================
log() {
    echo -e "${2:-$GREEN}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

show_help() {
    echo -e "${BLUE}=== Script de inicio para cine-platform ===${NC}"
    echo ""
    echo "Uso: ./scripts/start.sh [opciones]"
    echo ""
    echo "Opciones:"
    echo "  --build       Reconstruir imágenes antes de iniciar"
    echo "  --logs        Seguir los logs después de iniciar"
    echo "  --help        Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./scripts/start.sh                    # Iniciar sin reconstruir"
    echo "  ./scripts/start.sh --build            # Reconstruir e iniciar"
    echo "  ./scripts/start.sh --build --logs     # Reconstruir, iniciar y ver logs"
    echo ""
}

# ============================================
# IR AL DIRECTORIO DEL PROYECTO
# ============================================
cd "$PROJECT_DIR"
log "🚀 Iniciando cine-platform en modo producción" "$BLUE"
log "📁 Directorio: ${PROJECT_DIR}"
log "📁 Script: ${SCRIPT_DIR}"
log "📝 Log: ${LOG_FILE}"

# ============================================
# PROCESAR ARGUMENTOS
# ============================================
DO_BUILD=false
DO_LOGS=false

for arg in "$@"; do
    case $arg in
        --build)
            DO_BUILD=true
            shift
            ;;
        --logs)
            DO_LOGS=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Opción desconocida: $arg${NC}"
            show_help
            exit 1
            ;;
    esac
done

# ============================================
# VERIFICAR ARCHIVO COMPOSE
# ============================================
if [ ! -f "${COMPOSE_FILE}" ]; then
    log "❌ No se encuentra ${COMPOSE_FILE}" "$RED"
    exit 1
else
    log "✅ Archivo compose encontrado"
fi

# ============================================
# VERIFICAR ARCHIVOS .env
# ============================================
if [ ! -f ".env.prod" ]; then
    log "⚠️  No se encuentra .env.prod" "$YELLOW"
    log "   Creando desde plantilla si existe..."
    if [ -f ".env.example" ]; then
        cp .env.example .env.prod
        log "✅ .env.prod creado desde .env.example" "$GREEN"
    fi
else
    log "✅ .env.prod encontrado"
fi

# ============================================
# CREAR DIRECTORIO DE LOGS
# ============================================
mkdir -p "${PROJECT_DIR}/logs"

# ============================================
# LIMPIAR LOGS ANTIGUOS (OPCIONAL)
# ============================================
if [ -d "logs" ] && [ "$(ls -A logs 2>/dev/null)" ]; then
    LOG_SIZE=$(du -sh logs | cut -f1)
    log "📊 Logs existentes: ${LOG_SIZE}"
    
    # Borrar logs de más de 30 días
    find logs -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true
fi

# ============================================
# DETENER CONTENEDORES ANTIGUOS
# ============================================
log "🛑 Deteniendo contenedores antiguos..."
${COMPOSE_CMD} down --remove-orphans >> "$LOG_FILE" 2>&1

# ============================================
# RECONSTRUIR SI ES NECESARIO
# ============================================
if [ "$DO_BUILD" = true ]; then
    log "🔨 Reconstruyendo imágenes (esto puede tardar)..."
    ${COMPOSE_CMD} build --no-cache >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        log "✅ Imágenes reconstruidas correctamente"
    else
        log "❌ Error al reconstruir imágenes" "$RED"
        exit 1
    fi
else
    log "⏩ Usando imágenes existentes (usa --build para reconstruir)"
fi

# ============================================
# INICIAR CONTENEDORES
# ============================================
log "🚀 Iniciando contenedores..."
${COMPOSE_CMD} up -d >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    log "❌ Error al iniciar contenedores" "$RED"
    exit 1
fi

# ============================================
# MOSTRAR ESTADO INICIAL
# ============================================
log "📊 Estado inicial de los contenedores:"
${COMPOSE_CMD} ps

# ============================================
# ESPERAR A QUE POSTGRES ESTÉ LISTO
# ============================================
log "⏳ Esperando a que PostgreSQL esté listo..."
sleep 10

# ============================================
# VERIFICAR SALUD DE CONTENEDORES CRÍTICOS
# ============================================
log "🔍 Verificando salud de contenedores..."
CRITICAL_SERVICES=("postgres" "oauth2-server" "cine-postgres")

for service in "${CRITICAL_SERVICES[@]}"; do
    for i in {1..12}; do
        if ${COMPOSE_CMD} ps | grep -q "${service}.*healthy"; then
            log "✅ ${service} está saludable"
            break
        fi
        if [ $i -eq 12 ]; then
            log "⚠️  ${service} no está saludable después de 60s" "$YELLOW"
            ${COMPOSE_CMD} logs --tail 10 "$service"
        fi
        sleep 5
    done
done

# ============================================
# VERIFICAR ENDPOINTS
# ============================================
if command -v curl &> /dev/null; then
    log "🔍 Verificando endpoints..."
    sleep 5
    
    # OAuth2 healthcheck
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/actuator/health | grep -q "200"; then
        log "✅ OAuth2 server responde correctamente"
    else
        log "⚠️  OAuth2 server no responde aún" "$YELLOW"
    fi
    
    # Cine-platform healthcheck
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/auth/check | grep -q "200"; then
        log "✅ Cine-platform responde correctamente"
    else
        log "⚠️  Cine-platform no responde aún" "$YELLOW"
    fi
fi

# ============================================
# MOSTRAR INFORMACIÓN FINAL
# ============================================
log ""
log "=========================================" "$BLUE"
log "✅ SISTEMA INICIADO CORRECTAMENTE" "$GREEN"
log "=========================================" "$BLUE"
log ""
log "📌 Servicios disponibles:" "$BLUE"
echo "   📍 Cine-platform:    http://localhost:5000"
echo "   📍 OAuth2 Server:    http://localhost:8080"
echo "   📍 Prowlarr:         http://localhost:9696"
echo "   📍 Jackett:          http://localhost:9117"
echo "   📍 Transmission:     http://localhost:9091"
echo "   📍 FFmpeg API:       http://localhost:8082"
echo ""
log "📊 Comandos útiles:" "$YELLOW"
echo "   ./scripts/start.sh --logs     # Ver logs en tiempo real"
echo "   docker-compose -f ${COMPOSE_FILE} logs -f  # Ver todos los logs"
echo "   docker-compose -f ${COMPOSE_FILE} ps       # Ver estado"
echo "   docker-compose -f ${COMPOSE_FILE} down     # Detener todo"
echo ""
log "📝 Log de esta ejecución: ${LOG_FILE}" "$BLUE"

# ============================================
# SEGUIR LOGS SI SE SOLICITÓ
# ============================================
if [ "$DO_LOGS" = true ]; then
    log "📋 Siguiendo logs (Ctrl+C para salir)..."
    ${COMPOSE_CMD} logs -f
fi