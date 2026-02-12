# 🚀 Guía para poner en marcha el proyecto en local (Docker Desktop)

## 1. Requisitos previos

La persona necesita:

- **Docker Desktop** instalado  
- Acceso al repositorio GitHub del proyecto  
- Acceso a las imágenes Docker (si se usan desde un registry)

---

## 2. Descargar el proyecto desde GitHub

```bash
git clone https://github.com/felixmurcia/cine-platform.git
cd cine-platform
```

Esto deja el código en local.

---

## 3. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
SECRET_KEY=clave_super_secreta
MOVIES_FOLDER=/data/movies
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

Estas variables son las que usa cine‑platform actualmente.

---

## 4. Levantar cine‑platform en Docker Desktop

La aplicación expone el puerto **5000** y no depende de ningún servicio externo.

Ejecutar:

```bash
docker run -d \
  --name cine-platform \
  -p 5000:5000 \
  -e SECRET_KEY=clave_super_secreta \
  -e MOVIES_FOLDER=/data/movies \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/temp:/app/temp \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/logs:/app/logs \
  -v /ruta/a/tus/peliculas:/data/movies \
  felixmurcia/cine-platform:latest
```

Ajusta la ruta de películas según tu máquina.

---

## 5. Acceder a la aplicación

Abrir en el navegador:

```
http://localhost:5000
```

La autenticación se realiza mediante tu servidor OAuth2, no hay dependencias locales adicionales.

---

# 🧪 Comprobaciones si algo falla

### 1. Ver si el contenedor está corriendo

```bash
docker ps
```

Debe aparecer:

```
cine-platform   0.0.0.0:5000->5000/tcp
```

### 2. Ver variables de entorno dentro del contenedor

```bash
docker exec -it cine-platform env
```

### 3. Ver logs de la aplicación

```bash
docker logs cine-platform
```

---

# ⭐ BONUS: docker-compose (opcional)

Puedes levantar cine‑platform con un solo comando usando este archivo:

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  cine-platform:
    image: felixmurcia/cine-platform:latest
    ports:
      - "5000:5000"
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
      - ./temp:/app/temp
      - ./outputs:/app/outputs
      - ./logs:/app/logs
      - /ruta/a/tus/peliculas:/data/movies
```

Entonces solo necesitas:

```bash
docker compose up
```
