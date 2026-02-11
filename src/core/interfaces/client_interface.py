"""
Client interface definitions for external service interactions.

This module defines the abstract interfaces that all client implementations
must follow to ensure consistent external service interaction patterns.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic

T = TypeVar('T')

class ClientInterface(ABC):
    """
    Base interface for all client interfaces.
    """
    pass

class VectorDatabaseClientInterface(ABC):
    """Interface for vector database client operations."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the vector database."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the vector database."""
        pass
    
    @abstractmethod
    def create_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Create or update database schema.
        
        Args:
            schema: Schema definition
            
        Returns:
            bool: True if schema creation was successful
        """
        pass
    
    @abstractmethod
    def delete_schema(self) -> bool:
        """
        Delete entire database schema.
        
        Returns:
            bool: True if schema deletion was successful
        """
        pass
    
    @abstractmethod
    def create_object(self, class_name: str, properties: Dict[str, Any], vector: Optional[List[float]] = None) -> str:
        """
        Create a new object in the database.
        
        Args:
            class_name: Name of the class to create object in
            properties: Object properties
            vector: Optional vector for the object
            
        Returns:
            str: ID of created object
        """
        pass
    
    @abstractmethod
    def get_object(self, class_name: str, object_id: str) -> Optional[Dict[str, Any]]:
        """
        Get object by ID.
        
        Args:
            class_name: Name of the class
            object_id: ID of the object
            
        Returns:
            Optional[Dict[str, Any]]: Object data if found
        """
        pass
    
    @abstractmethod
    def update_object(self, class_name: str, object_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update object properties.
        
        Args:
            class_name: Name of the class
            object_id: ID of the object
            properties: Updated properties
            
        Returns:
            bool: True if update was successful
        """
        pass
    
    @abstractmethod
    def delete_object(self, class_name: str, object_id: str) -> bool:
        """
        Delete object by ID.
        
        Args:
            class_name: Name of the class
            object_id: ID of the object
            
        Returns:
            bool: True if deletion was successful
        """
        pass
    
    @abstractmethod
    def semantic_search(self, class_name: str, query_vector: List[float], limit: int = 10, certainty: float = 0.75) -> List[Dict[str, Any]]:
        """
        Perform semantic search.
        
        Args:
            class_name: Name of the class to search in
            query_vector: Vector to search with
            limit: Maximum number of results
            certainty: Minimum similarity threshold
            
        Returns:
            List[Dict[str, Any]]: List of matching objects
        """
        pass
    
    @abstractmethod
    def batch_create(self, class_name: str, objects: List[Dict[str, Any]], vectors: List[List[float]]) -> List[str]:
        """
        Create multiple objects in a batch.
        
        Args:
            class_name: Name of the class
            objects: List of object properties
            vectors: List of vectors for the objects
            
        Returns:
            List[str]: List of created object IDs
        """
        pass


class EmbeddingClientInterface(ABC):
    """Interface for embedding service client operations."""
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            List[float]: Embedding vector
        """
        pass
    
    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float]]: List of embedding vectors
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Returns:
            Dict[str, Any]: Model information
        """
        pass 