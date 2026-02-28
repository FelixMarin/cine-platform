# Documentación de la Nueva Arquitectura - Cine Platform

## 📋 Resumen

El proyecto ha sido refactorizado siguiendo los principios de la **Arquitectura Hexagonal (Ports and Adapters)** y los principios **SOLID**.

## 🏗️ Estructura del Proyecto

```
src/
├── core/                          ← DOMINIO (sin dependencias externas)
│   ├── entities/                   ← Entidades del negocio
│   │   ├── movie.py               # Película
│   │   ├── serie.py               # Serie + Episode
│   │   ├── user.py                # Usuario
│   │   └── progress.py            # Progreso de reproducción
│   │
│   ├── use_cases/                  ← Casos de uso (lógica de negocio)
│   │   ├── catalog/               # Listado y búsqueda
│   │   ├── player/                # Streaming y progreso
│   │   ├── optimizer/             # Optimización de video
│   │   └── auth/                  # Autenticación
│   │
│   └── ports/                      ← Interfaces (puertos)
│       ├── repositories/           # Interfaces de repositorios
│       │   ├── movie_repository.py
│       │   ├── serie_repository.py
│       │   ├── episode_repository.py
│       │   ├── user_repository.py
│       │   └── progress_repository.py
│       └── services/              # Interfaces de servicios
│           ├── metadata_service.py
│           ├── encoder_service.py
│           ├── queue_service.py
│           └── auth_service.py
│
├── adapters/                       ← ADAPTADORES
│   ├── entry/                      # Adaptadores de entrada
│   │   └── web/routes/            # Rutas Flask
│   │       ├── catalog.py
│   │       ├── player.py
│   │       ├── auth.py
│   │       └── optimizer.py
│   │
│   ├── outgoing/                   # Adaptadores de salida
│   │   ├── repositories/
│   │   │   ├── postgresql/       # Implementaciones PostgreSQL
│   │   │   └── filesystem/       # Implementación Filesystem
│   │   └── services/
│   │       ├── omdb/             # Cliente OMDB
│   │       └── ffmpeg/           # Servicio FFmpeg
│   │
│   └── config/
│       └── dependencies.py        # Inyección de dependencias
│
└── infrastructure/                 ← Configuración técnica
    └── config/
        └── settings.py            # Configuración centralizada
```

## 🔄 Flujo de Datos

```
Usuario → Rutas Flask (Adaptador de entrada)
              ↓
         Casos de Uso (Core)
              ↓
         Repositorios/Servicios (Puerto)
              ↓
    Implementaciones (Adaptador de salida) → PostgreSQL, Filesystem, OMDB, FFmpeg
```

## ✨ Nuevas Funcionalidades

### "Seguir Viendo"

La nueva arquitectura incluye soporte nativo para "Seguir viendo":

```python
# Endpoint: GET /api/continue-watching
# Retorna lista de contenidos con progreso activo

from src.core.use_cases.player import GetContinueWatchingUseCase

use_case = GetContinueWatchingUseCase(progress_repo, movie_repo, episode_repo)
result = use_case.execute(user_id=1, limit=10)
```

### Badges de "Visto"

```python
# Endpoint: GET /api/watched
# Retorna lista de contenidos completados

from src.core.use_cases.player import GetWatchedContentUseCase
```

## 🔌 Inyección de Dependencias

La configuración centralizada está en [`src/adapters/config/dependencies.py`](src/adapters/config/dependencies.py):

```python
from src.adapters.config import dependencies

# Inicializar con PostgreSQL
dependencies.init_all(use_postgresql=True)

# O con Filesystem (temporal)
dependencies.init_all(use_postgresql=False)

# Obtener casos de uso
list_movies = dependencies.get_list_movies_use_case()
track_progress = dependencies.get_track_progress_use_case()
```

## 🎯 Principios Aplicados

### Single Responsibility Principle (SRP)
- Cada entidad tiene una única responsabilidad
- Los casos de uso hacen una sola cosa
- Los adaptadores manejan un tipo de tecnología

### Open/Closed Principle (OCP)
- Las entidades están abiertas para extensión (herencia)
- Cerradas para modificación
- Nuevos adaptadores sin tocar el core

### Liskov Substitution Principle (LSP)
- Las interfaces definen contratos claros
- Los adaptadores pueden intercambiarse

### Interface Segregation Principle (ISP)
- Puertos pequeños y específicos
- IMovieRepository ≠ IUserRepository

### Dependency Inversion Principle (DIP)
- El core depende de abstracciones (puertos)
- Los adaptadores implementan abstracciones
- No hay dependencias del core hacia implementaciones

## 🚀 Próximos Pasos

1. **Conectar PostgreSQL**: Implementar las queries reales en los repositorios PostgreSQL
2. **Migrar rutas existentes**: Actualizar `modules/routes/` para usar la nueva estructura
3. **Tests**: Actualizar tests para usar los nuevos casos de uso
4. **Frontend**: Crear los carruseles de "Seguir viendo" y "Visto"

## 📝 Notas

- El código existente en `modules/` sigue funcionando (compatibilidad)
- La nueva estructura está en `src/`
- PostgreSQL está listo en Kubernetes, solo falta configurar la conexión
