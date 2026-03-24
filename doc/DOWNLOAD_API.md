# API de Descargas - Prowlarr y Transmission

Este documento describe los endpoints de API para buscar y descargar torrents usando Prowlarr y Transmission.

## Interfaz de Usuario

### Página de Búsqueda

La interfaz de búsqueda está disponible en: `GET /search`

Esta página proporciona:
- Campo de búsqueda para películas
- **Opción de entrada directa de URL (magnet o .torrent)**
- Selector de categoría persistente
- Resultados en formato de tarjetas
- Modal de progreso de descarga

**Acceso:** Navega a `/search` en el navegador.

### Modo URL Directa

La página de búsqueda incluye dos pestañas:

1. **🔎 Buscar película**: Busca en los indexadores de Prowlarr
2. **🔗 URL directa**: Permite pegar directamente una URL de torrent

En el modo URL directa puedes pegar:
- Links magnet (`magnet:?xt=urn:btih:...`)
- URLs de archivos `.torrent` (`https://example.com/torrent.torrent`)

El sistema validará automáticamente el formato y mostrará un error si no es válido.

**Características:**
- Validación básica de formato de URL
- Feedback visual inmediato
- Usa el mismo desplegable de categorías
- Mismo flujo de descarga que la búsqueda normal

### Seguimiento de Descargas

La interfaz incluye un sistema de seguimiento en tiempo real:

1. **Al iniciar una descarga**: Se abre un modal con el progreso
2. **Polling cada 2 segundos**: Actualiza automáticamente el progreso
3. **Información mostrada**:
   - Barra de progreso visual
   - Porcentaje de descarga
   - Velocidad de descarga
   - Tiempo restante estimado
4. **Acciones disponibles**:
   - Cerrar modal
   - Ver todas las descargas

## Endpoints Disponibles

### 1. Buscar películas en Prowlarr

**Endpoint:** `GET /api/search-movie`

Busca películas en los indexadores configurados en Prowlarr.

**Parámetros de Query:**
- `q` (string, requerido): Término de búsqueda
- `limit` (int, opcional): Número máximo de resultados (por defecto: 20)

**Ejemplo:**
```bash
curl "http://localhost:5000/api/search-movie?q=matrix&limit=10"
```

**Respuesta:**
```json
{
    "success": true,
    "results": [
        {
            "guid": "prowlarr://...",
            "title": "The Matrix 1999 1080p BluRay",
            "indexer": "RarBG",
            "size": 2345678901,
            "size_formatted": "2.18 GB",
            "seeders": 100,
            "leechers": 20,
            "magnet_url": "magnet:?xt=urn:btih:...",
            "torrent_url": "https://...",
            "publish_date": "2023-01-15",
            "categories": ["Movies", "HD"]
        }
    ],
    "query": "matrix",
    "count": 10
}
```

---

### 2. Iniciar descarga de torrent

**Endpoint:** `POST /api/download-torrent`

Inicia una descarga en Transmission.

**Cuerpo de la petición (JSON):**
```json
{
    "url": "magnet:?xt=urn:btih:...",
    "result_id": "prowlarr://123",
    "category": "Acción"
}
```

**Parámetros:**
- `url` (string, requerido): URL del torrent (magnet o .torrent)
- `result_id` (string, opcional): ID del resultado en Prowlarr
- `category` (string, opcional): Categoría (Acción, Drama, Comedia, etc.)

**Ejemplo:**
```bash
curl -X POST http://localhost:5000/api/download-torrent \
  -H "Content-Type: application/json" \
  -d '{"url": "magnet:?xt=urn:btih:...", "category": "Acción"}'
```

**Respuesta:**
```json
{
    "success": true,
    "download": {
        "id": "uuid-unico",
        "torrent_id": 123,
        "name": "The Matrix 1999 1080p BluRay",
        "category": "Acción",
        "status": "downloading",
        "download_dir": "/tmp/cineplatform/uploads",
        "hash": "ABC123..."
    },
    "message": "Descarga iniciada correctamente"
}
```

---

### 3. Consultar estado de descargas

**Endpoint:** `GET /api/download-status`

Obtiene el estado de las descargas. También puedes usar:
- `GET /api/downloads/active` - Solo descargas activas
- `GET /api/downloads/<id>/status` - Estado de una descarga específica

Obtiene el estado de las descargas activas.

**Parámetros de Query:**
- `status` (string, opcional): Filtrar por estado (`active`, `completed`, `all`)
- `category` (string, opcional): Filtrar por categoría

**Ejemplo:**
```bash
curl "http://localhost:5000/api/download-status?status=active"
```

**Respuesta:**
```json
{
    "success": true,
    "downloads": [
        {
            "id": 123,
            "name": "The Matrix 1999 1080p BluRay",
            "hash": "ABC123...",
            "status": 4,
            "status_display": "downloading",
            "progress": 45.5,
            "size_total": 2345678901,
            "size_downloaded": 1073741824,
            "size_formatted": "2.18 GB",
            "rate_download": 5242880,
            "eta": 3600,
            "eta_formatted": "1h 0m",
            "category": "Acción"
        }
    ],
    "stats": {
        "active_count": 1,
        "completed_count": 5,
        "total_count": 10
    },
    "count": 1
}
```

---

### 4. Detener descarga

**Endpoint:** `POST /api/download-stop/<torrent_id>`

Detiene una descarga activa.

**Ejemplo:**
```bash
curl -X POST http://localhost:5000/api/download-stop/123
```

**Respuesta:**
```json
{
    "success": true,
    "message": "Torrent 123 detenido"
}
```

---

### 5. Reanudar descarga

**Endpoint:** `POST /api/download-start/<torrent_id>`

Reanuda una descarga pausada.

**Ejemplo:**
```bash
curl -X POST http://localhost:5000/api/download-start/123
```

---

### 6. Eliminar descarga

**Endpoint:** `POST /api/download-remove/<torrent_id>`

Elimina una descarga de Transmission.

**Cuerpo de la petición (JSON):**
```json
{
    "delete_files": false
}
```

**Parámetros:**
- `delete_files` (bool, opcional): Si es `true`, elimina también los archivos descargados

**Ejemplo:**
```bash
curl -X POST http://localhost:5000/api/download-remove/123 \
  -H "Content-Type: application/json" \
  -d '{"delete_files": false}'
```

---

### 7. Estado de optimizaciones

**Endpoint:** `GET /api/optimize-status`

Obtiene el estado de las optimizaciones activas (por ahora retorna lista vacía).

**Ejemplo:**
```bash
curl http://localhost:5000/api/optimize-status
```

**Respuesta:**
```json
{
    "success": true,
    "optimizations": [],
    "count": 0,
    "message": "No hay optimizaciones activas. Usa el endpoint de optimización del CLI."
}
```

---

### 8. Obtener categorías disponibles

**Endpoint:** `GET /api/categories`

Obtiene las categorías disponibles para organizar descargas.

**Ejemplo:**
```bash
curl http://localhost:5000/api/categories
```

**Respuesta:**
```json
{
    "success": true,
    "categories": [
        "Acción",
        "Animación",
        "Aventura",
        "Ciencia Ficción",
        "Comedia",
        "Documental",
        "Drama",
        "Familia",
        "Fantasía",
        "Historia",
        "Música",
        "Misterio",
        "Romance",
        "Suspense",
        "Terror",
        "Western"
    ]
}
```

---

### 9. Test de conexión

**Endpoint:** `GET /api/download-test`

Prueba la conexión con Prowlarr y Transmission.

**Ejemplo:**
```bash
curl http://localhost:5000/api/download-test
```

**Respuesta:**
```json
{
    "success": true,
    "services": {
        "prowlarr": true,
        "transmission": true
    }
}
```

---

## Configuración de Variables de Entorno

Para que los endpoints funcionen correctamente, es necesario configurar las siguientes variables de entorno:

```bash
# Prowlarr
PROWLARR_URL=http://localhost:9696
PROWLARR_API_KEY=tu_api_key_de_prowlarr

# Transmission
TRANSMISSION_URL=http://localhost:9091
TRANSMISSION_RPC_URL=http://localhost:9091/transmission/rpc
TRANSMISSION_USERNAME=tu_usuario
TRANSMISSION_PASSWORD=tu_contraseña

# Carpeta de descargas
UPLOAD_FOLDER=/tmp/cineplatform/uploads
```

## Notas

- Las descargas se guardan en la carpeta `./uploads` (configurable mediante `UPLOAD_FOLDER`)
- Cada descarga tiene un ID único para seguimiento
- Los estados de torrent en Transmission son: `stopped`, `check queued`, `checking`, `download queued`, `downloading`, `seed queued`, `seeding`
- La gestión de errores está integrada en cada endpoint

---

## Endpoints de Optimización

### 10. Iniciar optimización

**Endpoint:** `POST /api/optimize/start`

Inicia una optimización de video con FFmpeg.

**Cuerpo de la petición (JSON):**
```json
{
    "input_path": "/path/to/input.mkv",
    "output_path": "/path/to/output.mp4",
    "category": "Acción",
    "profile": "balanced"
}
```

**Parámetros:**
- `input_path` (string, requerido): Ruta del archivo de entrada
- `output_path` (string, requerido): Ruta del archivo de salida
- `category` (string, opcional): Categoría (por defecto: Drama)
- `profile` (string, opcional): Perfil (balanced, high_quality, etc.)

**Respuesta:**
```json
{
    "success": true,
    "job_id": "uuid-del-trabajo",
    "message": "Optimización iniciada"
}
```

---

### 11. Estado de optimizaciones

**Endpoint:** `GET /api/optimize/status`

Obtiene el estado de las optimizaciones.

**Parámetros:**
- `job_id` (string, opcional): ID específico del trabajo
- `active_only` (bool, opcional): Solo trabajos activos

**Respuesta:**
```json
{
    "success": true,
    "optimizations": [
        {
            "id": "uuid",
            "input_path": "/path/to/input.mkv",
            "output_path": "/path/to/output.mp4",
            "category": "Acción",
            "profile": "balanced",
            "status": "running",
            "progress": 45.5,
            "metrics": {
                "current_time": 1800.5,
                "total_duration": 7200.0,
                "fps": 60.0,
                "bitrate": 2500000,
                "current_size": 1073741824,
                "estimated_size": 2345678901
            }
        }
    ],
    "count": 1
}
```

---

### 12. Cancelar optimización

**Endpoint:** `POST /api/optimize/cancel/<job_id>`

Cancela una optimización en curso.

---

### 13. Obtener perfiles

**Endpoint:** `GET /api/optimize/profiles`

Obtiene los perfiles de optimización disponibles.

**Perfiles disponibles:**
- `ultra_fast`: Móvil/3G - 480p
- `fast`: 4G - 480p
- `balanced`: WiFi - 720p
- `high_quality`: Fibra - 1080p
- `master`: Máxima calidad

---

## Post-procesamiento

Al completar una optimización, el sistema automáticamente:

1. **Mueve el archivo** a la carpeta definitiva basada en categoría
2. **Actualiza el catálogo** para que la película sea visible
3. **Limpia archivos temporales** de la carpeta de descargas

### Estructura de carpetas finales

```
/mnt/DATA_2TB/audiovisual/
├── mkv/
│   ├── action/
│   ├── animation/
│   ├── comedy/
│   ├── drama/
│   ├── horror/
│   └── ... (otras categorías)
```

### Manejo de duplicados

Si ya existe un archivo con el mismo nombre, el sistema añade un sufijo `_1`, `_2`, etc.
