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

# 🔥 FORZAR LIMPIEZA DE CACHÉ DE BUILDX
echo "🧹 Limpiando caché de buildx..."
docker buildx prune -f

# Crear builder si no existe
docker buildx inspect cinebuilder >/dev/null 2>&1 || docker buildx create --name cinebuilder --use

# 🔥 FORZAR BUILD SIN CACHÉ (--no-cache) Y CON PUSH DIRECTO
docker build --no-cache -t $FULL_IMAGE .
docker push $FULL_IMAGE
# docker buildx build \
#   --pull \
#   --platform linux/amd64 \
#   -t $FULL_IMAGE \
#   --push \
#   .

# 🔥 FORZAR PULL LOCAL DE LA IMAGEN RECIÉN SUBIDA (para evitar cache local)
echo "📥 Forzando pull local de la imagen..."
docker pull $FULL_IMAGE

echo "======================================"
echo "  📦 Aplicando YAMLs de producción"
echo "======================================"

kubectl apply -f k3s/cine-config.yaml
kubectl apply -f k3s/cine-secret.yaml
kubectl apply -f k3s/cine-deployment.yaml
kubectl apply -f k3s/cine-service.yaml

echo "======================================"
echo "  📝 Actualizando Deployment en Kubernetes"
echo "======================================"

kubectl set image deployment/$DEPLOYMENT \
  $DEPLOYMENT=$FULL_IMAGE \
  -n $NAMESPACE \
  --record

# Verificar que se actualizó
kubectl get deployment -n $NAMESPACE $DEPLOYMENT -o yaml | grep image:

echo "======================================"
echo "  🧹 Eliminando imágenes antiguas de cine-platform"
echo "======================================"

# Obtener todas las imágenes locales de cine-platform excepto la más reciente
IMAGES_TO_DELETE=$(docker images felixmurcia/cine-platform --format "{{.Repository}}:{{.Tag}} {{.CreatedAt}}" \
  | sort -k2 -r \
  | tail -n +2 \
  | awk '{print $1}')

# Borrar cada imagen antigua
for IMG in $IMAGES_TO_DELETE; do
  echo "🗑️  Eliminando imagen antigua: $IMG"
  docker rmi -f "$IMG" || true
done

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

kubectl logs -n $NAMESPACE -l app=$DEPLOYMENT --tail=50