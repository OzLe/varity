"""
Database factory for creating repository instances.

This module provides a factory for creating database repositories,
enabling dependency injection and easy swapping of implementations.
"""

from typing import Any, Dict, Optional, Type
import weaviate

from ...core.interfaces import RepositoryInterface
from .weaviate.weaviate_client import WeaviateClient
from .weaviate.repositories.document_repository import WeaviateDocumentRepository


class DatabaseFactory:
    """
    Factory for creating database repositories.

    This class creates repository instances based on configuration,
    enabling dependency injection and easy swapping of implementations.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the factory.

        Args:
            config: Database configuration. If None, uses defaults.
        """
        self.config = config or {}
        self._client = None

    @property
    def client(self) -> WeaviateClient:
        """
        Get or create the database client.

        Returns:
            WeaviateClient: Database client
        """
        if self._client is None:
            url = self.config.get("url", "http://localhost:8080")
            api_key = self.config.get("api_key")
            self._client = WeaviateClient(
                url=url,
                auth_client_secret=weaviate.AuthApiKey(
                    api_key
                ) if api_key else None,
                timeout_config=(
                    self.config.get("timeout_seconds", 60),
                    self.config.get("timeout_retries", 3)
                ),
                additional_headers=self.config.get("headers")
            )
        return self._client

    def create_repository(
        self,
        repository_type: Type[RepositoryInterface]
    ) -> RepositoryInterface:
        """
        Create a repository instance.

        Args:
            repository_type: Type of repository to create

        Returns:
            RepositoryInterface: Repository instance

        Raises:
            ValueError: If repository type is not supported
        """
        if repository_type == WeaviateDocumentRepository:
            return WeaviateDocumentRepository(self.client)
        else:
            raise ValueError(f"Unsupported repository type: {repository_type}")
    
    async def close(self) -> None:
        """Close the database client."""
        if self._client is not None:
            await self._client.close()
            self._client = None 