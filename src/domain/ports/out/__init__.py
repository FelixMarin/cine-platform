"""
Domain ports - Output ports for repositories and services
"""
# Repository ports
from src.domain.ports.out.repositories import (
    IMovieRepository,
    ISerieRepository,
    IEpisodeRepository,
    IUserRepository,
    IProgressRepository,
)

# Service ports
from src.domain.ports.out.services import (
    IAuthService,
    IEncoderService,
    IQueueService,
    IFileFinder,
    ICleanupService,
    INameSanitizer,
    IOptimizerAPI,
    IOptimizationHistoryService,
    ITokenDecoder,
)

# IMetadataService is defined inline in services/__init__.py
from src.domain.ports.out.services import IMetadataService

# Comment repository port
from src.domain.ports.out.comment_repository_port import CommentRepositoryPort

__all__ = [
    # Repositories
    'IMovieRepository',
    'ISerieRepository',
    'IEpisodeRepository',
    'IUserRepository',
    'IProgressRepository',
    # Services
    'IAuthService',
    'IEncoderService',
    'IQueueService',
    'IFileFinder',
    'ICleanupService',
    'INameSanitizer',
    'IOptimizerAPI',
    'IOptimizationHistoryService',
    'ITokenDecoder',
    'IMetadataService',
    # Comments
    'CommentRepositoryPort',
]
