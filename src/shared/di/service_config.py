"""
Service configuration for dependency injection.

This module provides centralized service registration and configuration
for the dependency injection container.
"""

from typing import Optional

from .container import Container
from .service_registry import ServiceLifetime

from infrastructure.config.config_manager import ConfigManager
from infrastructure.database.factory import DatabaseFactory
from infrastructure.database.weaviate.weaviate_client import WeaviateClient
from infrastructure.database.weaviate.repositories.document_repository import WeaviateDocumentRepository
from infrastructure.external.translation_client import TranslationClient
from infrastructure.external.embedding_client import EmbeddingClient
from infrastructure.external.model_manager import ModelManager

from services.ingestion_service import IngestionService
from services.search_service import SearchService
from services.validation_service import ValidationService

from presentation.cli.formatters.output_formatter import OutputFormatter
from presentation.cli.handlers.cli_handler import CLIApplication
from presentation.cli.commands.ingestion_commands import (
    IngestCommand,
    ValidateCommand,
    StatusCommand
)
from presentation.cli.commands.search_commands import (
    SearchCommand,
    FilterCommand,
    StatsCommand
)


def configure_services(
    container: Container,
    config_path: Optional[str] = None,
    profile: Optional[str] = None
) -> None:
    """
    Configure services in the dependency injection container.
    
    Args:
        container: Container to configure
        config_path: Optional path to configuration file
        profile: Optional configuration profile
    """
    # Infrastructure services
    container.register_singleton(
        ConfigManager,
        lambda: ConfigManager(config_path, profile)
    )
    
    container.register_singleton(
        DatabaseFactory,
        lambda: DatabaseFactory(container.resolve(ConfigManager))
    )
    
    container.register_singleton(
        WeaviateClient,
        lambda: container.resolve(DatabaseFactory).create_client()
    )
    
    container.register_scoped(
        WeaviateDocumentRepository,
        lambda: WeaviateDocumentRepository(container.resolve(WeaviateClient))
    )
    
    container.register_singleton(
        TranslationClient,
        lambda: TranslationClient(container.resolve(ConfigManager))
    )
    
    container.register_singleton(
        EmbeddingClient,
        lambda: EmbeddingClient(container.resolve(ConfigManager))
    )
    
    container.register_singleton(
        ModelManager,
        lambda: ModelManager(container.resolve(ConfigManager))
    )
    
    # Application services
    container.register_transient(
        IngestionService,
        lambda: IngestionService(
            config_manager=container.resolve(ConfigManager),
            document_repository=container.resolve(WeaviateDocumentRepository),
            translation_client=container.resolve(TranslationClient),
            embedding_client=container.resolve(EmbeddingClient),
            model_manager=container.resolve(ModelManager)
        )
    )
    
    container.register_transient(
        SearchService,
        lambda: SearchService(
            document_repository=container.resolve(WeaviateDocumentRepository),
            embedding_client=container.resolve(EmbeddingClient)
        )
    )
    
    container.register_transient(
        ValidationService,
        lambda: ValidationService(
            document_repository=container.resolve(WeaviateDocumentRepository)
        )
    )
    
    # Presentation services
    container.register_singleton(
        OutputFormatter,
        OutputFormatter
    )
    
    container.register_singleton(
        CLIApplication,
        lambda: CLIApplication(container.resolve(OutputFormatter))
    )
    
    # CLI Commands
    container.register_transient(
        IngestCommand,
        lambda: IngestCommand(container.resolve(IngestionService))
    )
    
    container.register_transient(
        ValidateCommand,
        lambda: ValidateCommand(container.resolve(ValidationService))
    )
    
    container.register_transient(
        StatusCommand,
        lambda: StatusCommand(container.resolve(IngestionService))
    )
    
    container.register_transient(
        SearchCommand,
        lambda: SearchCommand(container.resolve(SearchService))
    )
    
    container.register_transient(
        FilterCommand,
        lambda: FilterCommand(container.resolve(SearchService))
    )
    
    container.register_transient(
        StatsCommand,
        lambda: StatsCommand(container.resolve(SearchService))
    ) 