# 🚀 Guía para poner en marcha el proyecto en local (Docker Desktop)

## 1. Requisitos previos

Antes de empezar, la persona necesita:

- **Docker Desktop** instalado  
- Acceso al repositorio GitHub del proyecto  
- Acceso a las imágenes Docker (GHCR o Docker Hub)

---

## 2. Descargar el proyecto desde GitHub

En cualquier terminal:

```bash
git clone https://github.com/felixmurcia/cine-platform.git
cd cine-platform
```

Esto deja el código en local.

---

## 3. Levantar PocketBase (base de datos + auth)

PocketBase es obligatorio para que cine‑platform funcione.

Ejecutar:

```bash
docker run -d \
  --name pocketbase \
  -p 8090:8090 \
  ghcr.io/muchobien/pocketbase:latest
```

Esto deja PocketBase accesible en:

```
http://localhost:8090/_/
```

### 3.1. Crear usuario administrador

1. Abrir navegador  
2. Ir a: `http://localhost:8090/_/`  
3. Crear usuario admin  
4. (Opcional) Crear colecciones necesarias si el proyecto las requiere

---

## 4. Levantar cine‑platform

cine‑platform necesita saber dónde está PocketBase.  
En Docker Desktop, la forma correcta es:

```
http://host.docker.internal:8090
```

Ejecutar:

```bash
docker run -d \
  --name cine-platform \
  -p 5000:5000 \
  -e POCKETBASE_URL=http://host.docker.internal:8090 \
  ghcr.io/felixmurcia/cine-platform:v1.0.0
```

---

## 5. Acceder a la aplicación

Abrir:

```
http://localhost:5000
```

Y logearse con el usuario creado en PocketBase.

---

# 🧪 Comprobaciones si algo falla

### 1. Ver si PocketBase está corriendo

```bash
docker ps
```

Debe aparecer:

```
pocketbase   0.0.0.0:8090->8090/tcp
```

### 2. Ver si cine‑platform tiene la variable correcta

```bash
docker exec -it cine-platform env | grep POCKET
```

Debe mostrar:

```
POCKETBASE_URL=http://host.docker.internal:8090
```

### 3. Ver logs de cine‑platform

```bash
docker logs cine-platform
```

Si no puede conectar a PocketBase, lo verás ahí.

---

# ⭐ BONUS: docker-compose (opcional pero recomendado)

Para que todo arranque con un solo comando, añade este archivo al repo:

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  pocketbase:
    image: ghcr.io/muchobien/pocketbase:latest
    ports:
      - "8090:8090"
    volumes:
      - pb_data:/pb_data

  cine-platform:
    image: ghcr.io/felixmurcia/cine-platform:v1.0.0
    ports:
      - "5000:5000"
    environment:
      - POCKETBASE_URL=http://pocketbase:8090
    depends_on:
      - pocketbase

volumes:
  pb_data:
```

Entonces solo necesitan:

```bash
docker compose up
```

y todo funciona automáticamente.
