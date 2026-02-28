# 📘 README — Entorno de Desarrollo con Tilt en k3s

Este documento explica cómo instalar, configurar y ejecutar **Tilt** para desarrollar aplicaciones dentro de un clúster **k3s**, con hot‑reload y sin necesidad de reconstruir imágenes ni hacer push a Docker Hub.

Funciona para:

- `cine-platform`
- `transcriberapp`
- cualquier otro servicio que quieras añadir

---

## 🧩 Requisitos previos

Antes de usar Tilt necesitas:

### ✔ k3s instalado y funcionando  
En el Jetson, normalmente:

```
sudo systemctl status k3s
```

### ✔ kubectl configurado  
Debe apuntar al clúster k3s:

```
kubectl get nodes
```

### ✔ containerd (viene con k3s)  
Tilt lo usará para inyectar imágenes sin Docker.

### ✔ Python / Flask / Uvicorn según tu proyecto  
Tilt no instala dependencias, solo sincroniza código.

---

## 🛠 Instalación de Tilt

Tilt se instala con un script oficial:

```
curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash
```

Comprueba que funciona:

```
tilt version
```

---

## 📁 Estructura esperada del proyecto

Cada servicio debe tener:

```
/cine-platform
  Tiltfile
  cine-deployment-dev.yaml
  Dockerfile
  app.py
  ...

/transcriberapp
  Tiltfile
  transcriberapp-deployment-dev.yaml
  Dockerfile
  transcriber_app/
  ...
```

---

## ⚙ Configuración de Tilt para k3s

Tilt necesita saber que tu clúster usa **containerd**, no Docker.

Por eso, en cada Tiltfile se usa:

```python
docker_build(
    "nombre-imagen-dev",
    context=".",
    dockerfile="Dockerfile",
    container_runtime="containerd",
    live_update=[
        sync(".", "/app"),
        run("touch /app/reload.trigger"),
    ],
)
```

Esto permite:

- hot‑reload real  
- sincronización instantánea de código  
- sin push a Docker Hub  
- sin reinicios lentos  

---

## 🚀 Ejecutar Tilt

Entra en el directorio del servicio:

```
cd cine-platform
```

o

```
cd transcriberapp
```

Lanza Tilt:

```
tilt up
```

Se abrirá la interfaz web:

```
http://localhost:10350
```

---

## 🔥 Hot‑reload en acción

Cada vez que guardes un archivo:

- Tilt sincroniza el cambio dentro del contenedor  
- Flask/Uvicorn recargan automáticamente  
- No hay builds  
- No hay pushes  
- No hay rollouts  

Es el equivalente a `docker-compose up --build` pero dentro de k3s.

---

## 🧹 Parar Tilt

```
tilt down
```

Esto elimina los recursos creados por Tilt, pero **no borra PVCs ni datos**.

---

## 🧪 Comprobación rápida

Para verificar que Tilt está usando tu imagen local:

```
kubectl get pods
kubectl describe pod <nombre>
```

Debe aparecer:

```
Image: cine-platform-dev
```

o

```
Image: transcriberapp-dev
```

---

## 🛑 Problemas comunes

### ❌ Tilt no actualiza el pod  
Solución: asegúrate de que el Tiltfile tiene:

```
container_runtime="containerd"
```

### ❌ El código no se sincroniza  
Solución: revisa que el Deployment tenga:

```
volumeMounts:
  - name: src
    mountPath: /app

volumes:
  - name: src
    hostPath:
      path: /ruta/local/del/proyecto
```

### ❌ Uvicorn/Flask no recargan  
Solución: usa:

```
--reload
```

en el comando del contenedor.

---

## 🎯 Resumen

Tilt te permite:

- desarrollar dentro de k3s  
- con hot‑reload real  
- sin builds lentos  
- sin pushes  
- sin rollouts  
- sin reiniciar pods  
