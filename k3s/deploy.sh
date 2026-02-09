#!/bin/bash

set -e

# ===== CONFIGURACIÓN =====
IMAGE_NAME="felixmurcia/cine-platform"
NAMESPACE="cine"
DEPLOYMENT="cine-platform"

# ===== GENERAR TAG AUTOMÁTICO =====
TAG=$(date +"v%Y%m%d-%H%M")
FULL_IMAGE="$IMAGE_NAME:$TAG"

echo "======================================"
echo "  🚀 Construyendo imagen: $FULL_IMAGE"
echo "======================================"

docker build -t $FULL_IMAGE .

echo "======================================"
echo "  📤 Subiendo imagen a Docker Hub"
echo "======================================"

docker push $FULL_IMAGE

echo "======================================"
echo "  📝 Actualizando Deployment en Kubernetes"
echo "======================================"

kubectl set image deployment/$DEPLOYMENT \
  $DEPLOYMENT=$FULL_IMAGE \
  -n $NAMESPACE

echo "======================================"
echo "  🔄 Forzando rollout"
echo "======================================"

kubectl rollout restart deployment/$DEPLOYMENT -n $NAMESPACE

echo "======================================"
echo "  ⏳ Esperando a que el nuevo pod esté listo"
echo "======================================"

kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE

echo "======================================"
echo "  🧹 Limpiando imágenes antiguas de Docker"
echo "======================================"

# Elimina imágenes dangling (sin tag)
docker image prune -f

# Elimina contenedores parados
docker container prune -f

# Elimina imágenes que no se han usado en 30 días
docker image prune -a --filter "until=720h" -f

echo "======================================"
echo "  📜 Logs del nuevo pod"
echo "======================================"

kubectl logs -n $NAMESPACE -l app=$DEPLOYMENT -f
