# ============================================
#  Tiltfile para desarrollo de cine-platform (k3s)
# ============================================

IMAGE_NAME = "cine-platform-dev"

docker_build(
    IMAGE_NAME,
    context=".",
    dockerfile="Dockerfile",
    container_runtime="containerd",   # IMPORTANTE para k3s
    live_update=[
        sync(".", "/app"),            # Sincroniza código local
        run("touch /app/reload.trigger"),
    ],
)

k8s_yaml("cine-deployment-dev.yaml")

k8s_resource(
    "cine-platform",
    port_forwards=[5000],
    image=IMAGE_NAME
)
