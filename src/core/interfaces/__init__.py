"""
Core interfaces module for Varity semantic search.

This module provides access to all core interfaces used throughout
the application.
"""

from .repository_interface import RepositoryInterface
from .service_interface import (
    IngestionServiceInterface,
    SearchServiceInterface,
    TranslationServiceInterface
)
from .client_interface import (
    VectorDatabaseClientInterface,
    EmbeddingClientInterface,
    ClientInterface
)

__all__ = [
    'RepositoryInterface',
    'IngestionServiceInterface',
    'SearchServiceInterface',
    'TranslationServiceInterface',
    'VectorDatabaseClientInterface',
    'EmbeddingClientInterface',
    'ClientInterface'
] 