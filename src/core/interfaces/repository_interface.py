"""
Repository interface definitions for ESCO data access.

This module defines the abstract interfaces that all repository implementations
must follow to ensure consistent data access patterns across the application.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic
import numpy as np

T = TypeVar('T')

class RepositoryInterface(Generic[T], ABC):
    """
    Base repository interface defining common operations for all repositories.
    
    This interface defines the contract that all repository implementations must follow,
    ensuring consistent data access patterns across the application.
    
    Type Parameters:
        T: The type of entity this repository handles
    """
    
    @abstractmethod
    def create(self, data: Dict[str, Any], vector: Optional[List[float]] = None) -> str:
        """
        Create a new entity in the database.
        
        Args:
            data: Dictionary containing entity data
            vector: Optional embedding vector for the entity
            
        Returns:
            str: URI of the created entity
            
        Raises:
            RepositoryError: If creation fails
        """
        pass
    
    @abstractmethod
    def get_by_uri(self, uri: str) -> Optional[T]:
        """
        Get an entity by its URI.
        
        Args:
            uri: URI of the entity to retrieve
            
        Returns:
            Optional[T]: The entity if found, None otherwise
            
        Raises:
            RepositoryError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def update(self, uri: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing entity.
        
        Args:
            uri: URI of the entity to update
            data: Dictionary containing updated entity data
            
        Returns:
            bool: True if update was successful, False otherwise
            
        Raises:
            RepositoryError: If update fails
        """
        pass
    
    @abstractmethod
    def delete(self, uri: str) -> bool:
        """
        Delete an entity by its URI.
        
        Args:
            uri: URI of the entity to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            RepositoryError: If deletion fails
        """
        pass
    
    @abstractmethod
    def search(self, query_vector: np.ndarray, limit: int = 10, certainty: float = 0.75) -> List[T]:
        """
        Perform semantic search using a query vector.
        
        Args:
            query_vector: Vector to search with
            limit: Maximum number of results to return
            certainty: Minimum similarity threshold
            
        Returns:
            List[T]: List of matching entities
            
        Raises:
            RepositoryError: If search fails
        """
        pass
    
    @abstractmethod
    def batch_create(self, data_list: List[Dict[str, Any]], vectors: List[np.ndarray]) -> List[str]:
        """
        Create multiple entities in a batch.
        
        Args:
            data_list: List of entity data dictionaries
            vectors: List of embedding vectors for the entities
            
        Returns:
            List[str]: List of URIs for created entities
            
        Raises:
            RepositoryError: If batch creation fails
        """
        pass
    
    @abstractmethod
    def exists(self, uri: str) -> bool:
        """
        Check if an entity exists by its URI.
        
        Args:
            uri: URI to check
            
        Returns:
            bool: True if entity exists, False otherwise
            
        Raises:
            RepositoryError: If check fails
        """
        pass
    
    @abstractmethod
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            
        Returns:
            List[T]: List of entities
            
        Raises:
            RepositoryError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get total number of entities.
        
        Returns:
            int: Total count of entities
            
        Raises:
            RepositoryError: If count fails
        """
        pass 