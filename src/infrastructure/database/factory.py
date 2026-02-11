"""
Database factory for creating repository instances.

This module provides a factory for creating database repositories,
enabling dependency injection and easy swapping of implementations.
"""

from typing import Dict, Any, Optional, Type
import weaviate

from ...core.interfaces import RepositoryInterface
from .weaviate.weaviate_client import WeaviateClient
from .weaviate.repositories.document_repository import WeaviateDocumentRepository
from .weaviate.repositories.occupation_repository import WeaviateOccupationRepository
from .weaviate.repositories.skill_repository import WeaviateSkillRepository


class DatabaseFactory:
    """
    Factory for creating database repositories.
    
    This class creates repository instances based on configuration,
    enabling dependency injection and easy swapping of implementations.
    """
    
    def __init__(
        self,
        config: Dict[str, Any]
    ):
        """
        Initialize the factory.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self._client = None
    
    @property
    def client(self) -> WeaviateClient:
        """
        Get or create the database client.
        
        Returns:
            WeaviateClient: Database client
        """
        if self._client is None:
            self._client = WeaviateClient(
                url=self.config["url"],
                auth_client_secret=weaviate.AuthApiKey(
                    self.config.get("api_key")
                ) if self.config.get("api_key") else None,
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
        elif repository_type == WeaviateOccupationRepository:
            return WeaviateOccupationRepository(self.client)
        elif repository_type == WeaviateSkillRepository:
            return WeaviateSkillRepository(self.client)
        else:
            raise ValueError(f"Unsupported repository type: {repository_type}")
    
    async def close(self) -> None:
        """Close the database client."""
        if self._client is not None:
            await self._client.close()
            self._client = None 