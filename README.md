# Cine Platform

Plataforma unificada que combina streaming de películas/series y optimización de videos, refactorizada bajo **Arquitectura Hexagonal** y totalmente **Dockerizada**.

## 🎯 Características

- **Streaming de Películas y Series**: Navegación, reproducción y descarga de contenido multimedia
- **Optimizador de Videos**: Pipeline de procesamiento FFmpeg con soporte para GPU Jetson
- **Autenticación Unificada**: Login único con PocketBase para todas las funcionalidades
- **Panel de Administración**: Gestión avanzada para usuarios con rol admin
- **Procesamiento en Tiempo Real**: Monitoreo del estado de optimización de videos
- **Despliegue con Docker**: Entorno aislado y reproducible con Docker Compose

## 🏗️ Arquitectura Hexagonal

El proyecto ha sido refactorizado para seguir los principios de la Arquitectura Hexagonal (Ports & Adapters), desacoplando la lógica de negocio de los detalles de implementación:

- **Dominio**: Lógica central de la aplicación.
- **Adaptadores (Infrastructure)**:
  - **Auth**: Adaptador para PocketBase (`PocketBaseAuthAdapter`).
  - **Media**: Repositorio de sistema de archivos (`FileSystemMediaRepository`).
  - **Optimizer**: Adaptador para FFmpeg (`FFmpegOptimizerAdapter`).
  - **Web**: Adaptador HTTP con Flask (`modules.routes`).

## 📋 Requisitos Previos

- **Docker y Docker Compose** (Recomendado)
- Python 3.8+ (Para ejecución local manual)
- FFmpeg instalado en el sistema (Para ejecución local manual)
- PocketBase (Incluido automáticamente en Docker)

## 🚀 Instalación

### Opción A: Docker (Recomendado)

Esta opción levanta la aplicación y una instancia de PocketBase automáticamente, evitando conflictos de dependencias.

1. **Configurar volúmenes**:
   Verifica en `docker-compose.yml` que la ruta de tus películas coincida con tu sistema (por defecto `/media/d/audiovisual`).

2. **Iniciar servicios**:
   ```bash
   docker compose up -d --build
   ```

3. **Acceder**:
   - **Cine Platform**: `http://localhost:5000`
   - **PocketBase (Docker)**: `http://localhost:8071/_/` (Puerto modificado para evitar conflictos con instancias locales).

### Opción B: Ejecución Manual (Local)

1. **Clonar o navegar al directorio del proyecto**:
   ```bash
   cd /home/jetson/Public/cine-app/cine-platform
   ```

2. **Activar el entorno virtual**:
   ```bash
   source ../env/bin/activate
   ```

3. **Verificar dependencias** (ya instaladas en el venv compartido):
   ```bash
   pip list | grep -E "Flask|requests|pocketbase"
   ```

## ⚙️ Configuración

Edita el archivo `.env` para personalizar la configuración:

```env
# Flask Configuration
SECRET_KEY=tu_clave_secreta_aqui
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# PocketBase Authentication
POCKETBASE_URL=http://127.0.0.1:8070

# Movie Streaming
MOVIES_FOLDER=/media/d/audiovisual

# Video Optimization
UPLOAD_FOLDER=./uploads
TEMP_FOLDER=./temp
OUTPUT_FOLDER=./outputs
```

## 🎬 Uso

### Iniciar el Servidor

```bash
# Desde el directorio cine-platform
source ../env/bin/activate
python server.py
```

El servidor se iniciará en:
- **Local**: `http://127.0.0.1:5000`
- **Red local**: `http://192.168.0.105:5000` (o tu IP local)

### Detener el Servidor

Presiona `Ctrl+C` en la terminal donde está corriendo el servidor.

Si necesitas forzar la detención:
```bash
pkill -f "python.*server.py"
```

## 🌐 Acceso a las Interfaces

### 1. Login
- **URL**: `http://localhost:5000/login`
- **Credenciales**: Usa tus credenciales de PocketBase
- Después del login exitoso, serás redirigido al dashboard principal

### 2. Dashboard Principal (Streaming)
- **URL**: `http://localhost:5000/`
- **Funcionalidades**:
  - Ver catálogo de películas
  - Ver catálogo de series organizadas por temporadas
  - Reproducir contenido directamente en el navegador
  - Descargar archivos
  - Acceso rápido al optimizador (botón verde "🎬 OPTIMIZADOR")
  - Panel admin (solo usuarios con rol admin)

### 3. Optimizador de Videos
- **URL**: `http://localhost:5000/optimizer`
- **Funcionalidades**:
  - Subir videos para optimización
  - Monitorear progreso en tiempo real
  - Ver información del video original
  - Consultar historial de procesamiento
  - Descargar videos optimizados
  - Volver al dashboard principal (botón "← Volver al inicio")

### 4. Panel de Administración
- **URL**: `http://localhost:5000/admin/manage`
- **Requisito**: Usuario con rol `admin` en PocketBase
- **Funcionalidades**: Gestión avanzada del sistema

## 📊 API Endpoints

### Autenticación
- `GET/POST /login` - Inicio de sesión
- `GET /logout` - Cerrar sesión

### Streaming
- `GET /` - Dashboard principal
- `GET /play/<path>` - Reproductor de video
- `GET /stream/<path>` - Stream de video con soporte HTTP Range
- `GET /thumbnails/<filename>` - Miniaturas generadas
- `GET /download/<path>` - Descarga de archivos

### Optimizador
- `GET /optimizer` - Interfaz del optimizador
- `POST /process-file` - Subir y procesar video individual
- `POST /process` - Procesar carpeta de videos
- `GET /status` - Estado del procesamiento (JSON)
- `GET /outputs/<filename>` - Descargar videos optimizados

## 🔧 Pipeline de Optimización

El optimizador ejecuta 4 pasos automáticamente:

1. **Reparar Archivo**: Corrige posibles corrupciones usando `ffmpeg -c copy`
2. **Reducir Tamaño**: Reduce resolución a 720p y bitrate a 2M
3. **Optimizar Video**: Codifica con preset optimizado y CRF 23
4. **Validar Duración**: Verifica que la duración coincida con el original

### Soporte GPU (Jetson)

El sistema detecta automáticamente hardware Jetson y utiliza:
- **Decoder**: `h264_nvv4l2dec` (aceleración por hardware)
- **Encoder**: `libx264` (CPU, ya que Jetson Orin Nano no tiene NVENC)

## 📁 Estructura de Directorios

```
cine-platform/
├── server.py              # Servidor Flask unificado
├── .env                   # Configuración (no versionado)
├── requirements.txt       # Dependencias Python
├── Dockerfile             # Definición de imagen Docker
├── docker-compose.yml     # Orquestación de servicios
├── pb_client.py          # Cliente PocketBase
├── modules/              # Módulos (Arquitectura Hexagonal)
│   ├── adapter.py       # Adaptador de Optimización
│   ├── auth.py          # Adaptador de Autenticación
│   ├── media.py         # Adaptador de Medios
│   ├── routes.py        # Adaptador Web (Rutas)
│   └── logging/
│       └── logging_config.py
├── static/               # Assets frontend
│   ├── css/
│   ├── js/
│   └── images/
├── templates/            # Plantillas HTML
│   ├── index.html       # Dashboard principal
│   ├── login.html       # Login
│   ├── play.html        # Reproductor
│   └── optimizer.html   # Optimizador
├── uploads/             # Videos subidos (temporal)
├── temp/                # Procesamiento temporal
├── outputs/             # Videos optimizados
└── logs/                # Logs de la aplicación
```

## 📝 Logs

Los logs se guardan en:
- **Archivo**: `logs/cine-platform.log`
- **Consola**: Salida estándar durante ejecución

Nivel de log por defecto: `DEBUG`

## 🔐 Seguridad

- Todas las rutas (excepto `/login` y `/status`) requieren autenticación
- Las sesiones se gestionan con Flask sessions
- El panel admin requiere rol específico en PocketBase
- Los archivos sensibles (`.env`, `logs/`, `uploads/`) están en `.gitignore`

## 🐛 Troubleshooting

### Puerto 5000 ya en uso
```bash
# Ver qué proceso usa el puerto
sudo lsof -i :5000

# Detener el proceso
sudo kill -9 <PID>
```

### Error "Module not found"
```bash
# Asegúrate de activar el virtual environment
source ../env/bin/activate

# Verifica las dependencias
pip install -r requirements.txt
```

### PocketBase no responde
```bash
# Verifica que PocketBase esté corriendo
curl http://127.0.0.1:8070/api/health

# Ajusta POCKETBASE_URL en .env si es necesario
```

### FFmpeg no encontrado
```bash
# Instalar FFmpeg (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Verificar instalación
ffmpeg -version
```

## 📚 Recursos Adicionales

- **PocketBase**: https://pocketbase.io/docs/
- **Flask**: https://flask.palletsprojects.com/
- **FFmpeg**: https://ffmpeg.org/documentation.html

## 👥 Soporte

Para problemas o preguntas, consulta los logs en `logs/cine-platform.log` donde encontrarás información detallada sobre errores y operaciones del sistema.

---

**Versión**: 1.0.0  
**Última actualización**: 2026-02-08
