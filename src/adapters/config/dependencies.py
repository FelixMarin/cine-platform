"""
Configuración de Inyección de Dependencias

Este archivo es el corazón de la Arquitectura Hexagonal:
- Inicializa los adaptadores de salida (repositorios, servicios)
- Inicializa los casos de uso del core
- Proporciona las dependencias a las rutas

La arquitectura queda así:
                    ┌─────────────────────────────────────┐
                    │         ADAPTADORES DE ENTRADA       │
                    │  (Rutas Flask: catalog, player...)  │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │              CORE                   │
                    │  (Casos de Uso + Entidades + Puertos)│
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │        ADAPTADORES DE SALIDA        │
                    │  (PostgreSQL, Filesystem, OMDB...)  │
                    └─────────────────────────────────────┘
"""
import os
from typing import Optional

# === IMPORTS DE ADAPTADORES DE SALIDA ===

# Repositorios PostgreSQL
from src.adapters.outgoing.repositories.postgresql.movie_repository import PostgresMovieRepository
from src.adapters.outgoing.repositories.postgresql.progress_repository import PostgresProgressRepository

# Repositorios Filesystem
from src.adapters.outgoing.repositories.filesystem.movie_repository import FilesystemMovieRepository
from src.adapters.outgoing.repositories.filesystem.serie_repository import FilesystemSerieRepository

# Servicios externos
from src.adapters.outgoing.services.omdb.client import OMDBMetadataService
from src.adapters.outgoing.services.ffmpeg.encoder import FFmpegEncoderService
from src.adapters.outgoing.services.oauth.client import OAuth2Client

# === IMPORTS DE CASOS DE USO DEL CORE ===

# Catálogo
from src.core.use_cases.catalog import (
    ListMoviesUseCase,
    ListSeriesUseCase,
    SearchUseCase
)

# Player
from src.core.use_cases.player import (
    StreamMovieUseCase,
    StreamEpisodeUseCase,
    TrackProgressUseCase,
    GetContinueWatchingUseCase,
    GetWatchedContentUseCase
)

# Optimizer
from src.core.use_cases.optimizer import (
    OptimizeMovieUseCase,
    EstimateSizeUseCase
)

# Auth
from src.core.use_cases.auth import (
    LoginUseCase,
    LogoutUseCase
)

# === INSTANCIAS GLOBALES (SINGLETON) ===

# Repositorios
_movie_repository = None
_progress_repository = None
_serie_repository = None
_episode_repository = None
_user_repository = None

# Servicios
_metadata_service = None
_encoder_service = None
_oauth_service = None

# Casos de uso
_list_movies_use_case = None
_list_series_use_case = None
_search_use_case = None
_stream_movie_use_case = None
_stream_episode_use_case = None
_track_progress_use_case = None
_get_continue_watching_use_case = None
_get_watched_content_use_case = None
_optimize_movie_use_case = None
_estimate_size_use_case = None
_login_use_case = None
_logout_use_case = None

# === INICIALIZACIÓN DE DEPENDENCIAS ===

def get_database_connection():
    """
    Obtiene la conexión a PostgreSQL
    
    Returns:
        Conexión a la base de datos o None si no está configurada
    """
    # TODO: Implementar conexión real a PostgreSQL cuando esté lista
    # import psycopg2
    # return psycopg2.connect(
    #     host=os.environ.get('POSTGRES_HOST', 'localhost'),
    #     port=os.environ.get('POSTGRES_PORT', '5432'),
    #     database=os.environ.get('POSTGRES_DB', 'cineplatform'),
    #     user=os.environ.get('POSTGRES_USER', 'postgres'),
    #     password=os.environ.get('POSTGRES_PASSWORD', '')
    # )
    return None


def init_repositories(use_postgresql: bool = False):
    """
    Inicializa los repositorios
    
    Args:
        use_postgresql: Si True usa PostgreSQL, si False usa Filesystem
    """
    global _movie_repository, _progress_repository
    global _serie_repository, _episode_repository, _user_repository
    
    if use_postgresql:
        # Usar PostgreSQL
        db_conn = get_database_connection()
        _movie_repository = PostgresMovieRepository(db_conn)
        _progress_repository = PostgresProgressRepository(db_conn)
        _serie_repository = None  # TODO: Implementar
        _episode_repository = None  # TODO: Implementar
        _user_repository = None  # TODO: Implementar
    else:
        # Usar Filesystem (temporal/migración)
        base_folder = os.environ.get('MOVIES_FOLDER')
        _movie_repository = FilesystemMovieRepository(base_folder)
        _serie_repository = FilesystemSerieRepository(base_folder)
        _progress_repository = PostgresProgressRepository(None)  # Sin DB aún
        _episode_repository = None
        _user_repository = None


def init_services():
    """Inicializa los servicios externos"""
    global _metadata_service, _encoder_service, _oauth_service
    
    # OMDB Metadata Service
    _metadata_service = OMDBMetadataService()
    
    # FFmpeg Encoder Service
    _encoder_service = FFmpegEncoderService()
    
    # OAuth2 Service
    _oauth_service = OAuth2Client()


def init_use_cases():
    """Inicializa los casos de uso con sus dependencias"""
    global _list_movies_use_case, _list_series_use_case, _search_use_case
    global _stream_movie_use_case, _stream_episode_use_case
    global _track_progress_use_case
    global _get_continue_watching_use_case, _get_watched_content_use_case
    global _optimize_movie_use_case, _estimate_size_use_case
    global _login_use_case, _logout_use_case
    
    # Catálogo
    _list_movies_use_case = ListMoviesUseCase(_movie_repository)
    _list_series_use_case = ListSeriesUseCase(_serie_repository) if _serie_repository else None
    _search_use_case = SearchUseCase(_movie_repository, _serie_repository) if _serie_repository else None
    
    # Player
    _stream_movie_use_case = StreamMovieUseCase(_movie_repository, _progress_repository)
    _stream_episode_use_case = StreamEpisodeUseCase(_episode_repository, _progress_repository) if _episode_repository else None
    _track_progress_use_case = TrackProgressUseCase(
        _progress_repository,
        _movie_repository,
        _episode_repository
    )
    _get_continue_watching_use_case = GetContinueWatchingUseCase(
        _progress_repository,
        _movie_repository,
        _episode_repository
    )
    _get_watched_content_use_case = GetWatchedContentUseCase(
        _progress_repository,
        _movie_repository,
        _episode_repository
    )
    
    # Optimizer
    # TODO: Inicializar queue_service cuando esté implementado
    _optimize_movie_use_case = None  # OptimizeMovieUseCase(queue_service, _encoder_service)
    _estimate_size_use_case = EstimateSizeUseCase(_encoder_service)
    
    # Auth
    # TODO: Inicializar auth_service cuando esté implementado
    _login_use_case = None  # LoginUseCase(auth_service, _user_repository)
    _logout_use_case = None  # LogoutUseCase(auth_service)


def init_all(use_postgresql: bool = False):
    """
    Inicializa todas las dependencias
    
    Args:
        use_postgresql: Si True usa PostgreSQL, si False usa Filesystem
    """
    # 1. Inicializar repositorios
    init_repositories(use_postgresql)
    
    # 2. Inicializar servicios
    init_services()
    
    # 3. Inicializar casos de uso
    init_use_cases()


def get_list_movies_use_case() -> ListMoviesUseCase:
    """Obtiene el caso de uso de listar películas"""
    return _list_movies_use_case


def get_list_series_use_case():
    """Obtiene el caso de uso de listar series"""
    return _list_series_use_case


def get_search_use_case():
    """Obtiene el caso de uso de búsqueda"""
    return _search_use_case


def get_stream_movie_use_case():
    """Obtiene el caso de uso de streaming de película"""
    return _stream_movie_use_case


def get_stream_episode_use_case():
    """Obtiene el caso de uso de streaming de episodio"""
    return _stream_episode_use_case


def get_track_progress_use_case():
    """Obtiene el caso de uso de tracking de progreso"""
    return _track_progress_use_case


def get_continue_watching_use_case():
    """Obtiene el caso de uso de 'Seguir viendo'"""
    return _get_continue_watching_use_case


def get_watched_content_use_case():
    """Obtiene el caso de uso de contenido visto"""
    return _get_watched_content_use_case


def get_optimize_movie_use_case():
    """Obtiene el caso de uso de optimización"""
    return _optimize_movie_use_case


def get_estimate_size_use_case():
    """Obtiene el caso de uso de estimación de tamaño"""
    return _estimate_size_use_case


def get_login_use_case():
    """Obtiene el caso de uso de login"""
    return _login_use_case


def get_logout_use_case():
    """Obtiene el caso de uso de logout"""
    return _logout_use_case


def get_movie_repository():
    """Obtiene el repositorio de películas"""
    return _movie_repository


def get_progress_repository():
    """Obtiene el repositorio de progreso"""
    return _progress_repository


def get_metadata_service():
    """Obtiene el servicio de metadatos"""
    return _metadata_service


def get_encoder_service():
    """Obtiene el servicio de codificación"""
    return _encoder_service


def get_oauth_service():
    """Obtiene el servicio OAuth2"""
    return _oauth_service
