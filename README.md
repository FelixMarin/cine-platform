![Coverage](assets/coverage-badge.svg)
# Cine Platform

---

Plataforma unificada que combina **streaming de películas/series**, **optimización de vídeos** y un sistema de autenticación moderno basado en **OAuth2**, todo ello bajo una **Arquitectura Hexagonal** y completamente **Dockerizada**.

---

# 🎯 Características

- **Streaming de Películas y Series**: Navegación, reproducción y descarga de contenido multimedia  
- **Optimizador de Vídeos**: Pipeline FFmpeg con soporte para Jetson  
- **Autenticación OAuth2**: Login unificado mediante un servidor OAuth2 externo  
- **Panel de Administración**: Acceso restringido por roles (admin)  
- **Procesamiento en Tiempo Real**: Estado del optimizador accesible vía API  
- **Despliegue con Docker**: Entorno reproducible y aislado

---

# 🖼️ Sistema de Fallback para Pósters

El sistema de thumbnails implementa un **fallback automático** con esta prioridad:

1. **OMDB API** - Póster oficial desde la base de datos de OMDB
2. **Thumbnail Local** - Imagen almacenada en el sistema de archivos
3. **Imagen por Defecto** - `default.jpg` cuando no hay otras opciones

### Endpoint: `/api/movie-thumbnail`

```
GET /api/movie-thumbnail?title=<título>&year=<año>&filename=<filename>
```

**Parámetros:**
- `title` (requerido): Título de la película
- `year` (opcional): Año de lanzamiento
- `filename` (opcional): Nombre del archivo de video para fallback local

### Flujo de Búsqueda

1. **Primero**: Consulta OMDB API para obtener póster oficial
2. **Segundo**: Si OMDB no tiene datos, busca thumbnail local:
   - Ruta: configurable via `THUMBNAIL_FOLDER` (por defecto `/mnt/DATA_2TB/audiovisual/thumbnails`)
   - Nomenclatura: `[nombre]-[año]-optimized.jpg` o `.webp`
   - Ejemplo: `Red-One-(2023)-optimized.jpg`
3. **Tercero**: Devuelve 404 si no se encuentra ningún thumbnail

### Configuración

```env
# Archivos de medios
MOVIES_FOLDER=/mnt/DATA_2TB/audiovisual
THUMBNAIL_FOLDER=/mnt/DATA_2TB/audiovisual/thumbnails

# OMDB API (opcional)
OMDB_API_KEY=tu_api_key
```

### Logs de Debug

El endpoint genera logs para depuración:
- `🌐 OMDB OK: encontró póster para [película]` - OMDB tiene datos
- `⚠️ OMDB 404, buscando thumbnail local para [película]` - Sin datos en OMDB
- `✅ Thumbnail local encontrado: [archivo]` - Encontrado en sistema local
- `❌ Sin datos: usando default.jpg para [película]` - No hay thumbnail disponible

---

# 🏗️ Arquitectura Hexagonal

El proyecto sigue los principios de **Ports & Adapters**, desacoplando la lógica de negocio de los detalles de infraestructura.

### Dominios y Adaptadores

- **Dominio**: Lógica central de streaming y optimización  
- **Adaptadores (Infrastructure)**:
  - **Auth**: Adaptador OAuth2 (`OAuth2AuthAdapter`)
  - **Media**: Repositorio de sistema de archivos (`FileSystemMediaRepository`)
  - **Optimizer**: Adaptador FFmpeg (`FFmpegOptimizerAdapter`)
  - **Web**: Adaptador HTTP con Flask (`modules.routes`)

---

## Requisitos Previos

- **Docker / Docker Desktop**  
- Python 3.8+ (solo si se ejecuta manualmente)  
- FFmpeg instalado (solo ejecución manual)  
- Un servidor OAuth2 accesible (interno o externo)

---

# ⚠️ Dependencia con OAuth2Server

Esta aplicación **depende directamente** del servidor OAuth2 externo para la autenticación y gestión de usuarios.

## Repositorio Requerido

**OAuth2Server**: [https://github.com/FelixMarin/OAuth2Server](https://github.com/FelixMarin/OAuth2Server)

## Funcionalidades Dependientes

- **Login de usuarios**: El sistema de autenticación está delegado completamente en OAuth2Server
- **Gestión de usuarios**: Creación, modificación y eliminación de usuarios
- **Roles y permisos**: Administración de roles (admin, usuario estándar)
- **Tokens JWT**: Emisión y validación de tokens de sesión

----

- **Docker / Docker Desktop**  
- Python 3.8+ (solo si se ejecuta manualmente)  
- FFmpeg instalado (solo ejecución manual)  
- Un servidor OAuth2 accesible (interno o externo)

---

# 🚀 Instalación

## Opción A: Docker (Recomendada)

Imagen en Docker Hub:  
[https://hub.docker.com/repository/docker/felixmurcia/cine-platform/general](https://hub.docker.com/repository/docker/felixmurcia/cine-platform/general)

1. **Configurar volúmenes**  
   Asegúrate de que la ruta de tus películas coincide con tu sistema.

2. **Iniciar la aplicación**  
   ```bash
   docker compose up -d --build
   ```

3. **Acceder**  
   - Cine Platform: `http://localhost:5000`

> Nota: El servidor OAuth2 debe estar accesible desde el contenedor.

---

## Opción B: Ejecución Manual (Local)

1. Clonar el proyecto  
   ```bash
   cd /home/jetson/Public/cine-app/cine-platform
   ```

2. Activar entorno virtual  
   ```bash
   source ../env/bin/activate
   ```

3. Ejecutar  
   ```bash
   python server.py
   ```

---

# ⚙️ Configuración

Archivo `.env`:

```env
# Flask
SECRET_KEY=tu_clave_secreta
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# OAuth2 Server
OAUTH2_URL=http://tu-oauth2-server:8080

# Rutas internas
MOVIES_FOLDER=/data/movies
UPLOAD_FOLDER=./uploads
TEMP_FOLDER=./temp
OUTPUT_FOLDER=./outputs
LOG_FOLDER=./logs
```

---

# 🎬 Uso

## Iniciar el servidor

```bash
python server.py
```

Acceso:

- Local: `http://127.0.0.1:5000`
- Red local: `http://<tu-ip>:5000`

---

# 🌐 Interfaces

## 1. Login (OAuth2)
- URL: `http://localhost:5000/login`
- Redirección automática al servidor OAuth2
- Tras autenticación, se almacena un JWT en la sesión

## 2. Dashboard Principal
- URL: `/`
- Catálogo de películas y series  
- Reproducción y descarga  
- Acceso al optimizador  
- Panel admin (solo rol `admin`)

## 3. Optimizador de Vídeos
- URL: `/optimizer`
- Subida de vídeos  
- Progreso en tiempo real  
- Descarga de resultados  

## 4. Panel de Administración
- URL: `/admin/manage`
- Requiere rol `admin` en el JWT

---

# 📊 API Endpoints

### Autenticación
- `GET /login`
- `GET /logout`

### Películas y Series
- `GET /api/movies` - Lista de películas autenticado
- `GET /api/series` - Lista de series
- `GET /api/categories` - Categorías con películas y series
- `GET /api/search?q=<query>` - Búsqueda de contenido

### Thumbnails y Pósters
- `GET /api/movie-thumbnail?title=<title>&year=<year>&filename=<filename>` - Obtiene thumbnail de película (con fallback automático)
- `GET /api/serie-poster?name=<name>` - Obtiene póster de serie
- `GET /thumbnails/<filename>` - Servir thumbnail local

### Streaming
- `GET /`
- `GET /play/<path>`
- `GET /stream/<path>`
- `GET /thumbnails/<filename>`
- `GET /download/<path>`

### Optimizador
- `GET /optimizer`
- `POST /process-file`
- `POST /process`
- `GET /status`
- `GET /outputs/<filename>`

---

# 🔧 Pipeline de Optimización

1. Reparación del archivo  
2. Reducción de tamaño (720p, bitrate 2M)  
3. Optimización con CRF 23  
4. Validación de duración  

### Soporte Jetson

- Decoder: `h264_nvv4l2dec`  
- Encoder: `libx264`  

---

# 📁 Estructura del Proyecto

```
cine-platform/
├── server.py
├── modules/
│   ├── oauth/              # Adaptador OAuth2
│   ├── media/              # Repositorio de medios
│   ├── adapter.py          # FFmpeg Optimizer
│   ├── routes.py           # Rutas Flask
│   └── logging/
├── templates/
├── static/
├── uploads/
├── temp/
├── outputs/
└── logs/
```

---

# 📝 Logs

- Archivo: `logs/cine-platform.log`  
- Consola: salida estándar  
- Nivel por defecto: `DEBUG`

---

# 🔐 Seguridad

- Autenticación mediante OAuth2  
- Sesiones seguras con Flask  
- Roles incluidos en el JWT  
- Panel admin restringido  
- `.env`, `logs/`, `uploads/` ignorados en Git  

---

# 🐛 Troubleshooting

### Puerto 5000 ocupado
```bash
sudo lsof -i :5000
sudo kill -9 <PID>
```

### FFmpeg no encontrado
```bash
sudo apt install ffmpeg
ffmpeg -version
```

### OAuth2 no responde
```bash
curl http://tu-oauth2-server:8080/health
```

---

# 📚 Recursos

- **OAuth2**: [https://oauth.net/2/](https://oauth.net/2/)  
- **Flask**: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)  
- **FFmpeg**: [https://ffmpeg.org/documentation.html](https://ffmpeg.org/documentation.html)  

---

**Versión**: 2.1.0  
**Última actualización**: 2026-03-01
