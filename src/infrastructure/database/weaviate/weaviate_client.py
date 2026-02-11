"""
Weaviate client for database operations.

This module provides a client for interacting with Weaviate,
handling connections and basic operations.
"""

from typing import Dict, Any, Optional, List
import weaviate
from weaviate import Client
from weaviate.util import generate_uuid5

from ....core.interfaces import ClientInterface
from ....core.entities import (
    Document,
    SearchQuery,
    SearchResult
)


class WeaviateClient(ClientInterface):
    """
    Client for Weaviate database operations.
    
    This class handles connections to Weaviate and provides
    methods for basic database operations.
    """
    
    def __init__(
        self,
        url: str,
        auth_client_secret: Optional[weaviate.AuthApiKey] = None,
        timeout_config: Optional[tuple] = None,
        additional_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the client.
        
        Args:
            url: Weaviate instance URL
            auth_client_secret: Optional authentication credentials
            timeout_config: Optional timeout configuration
            additional_headers: Optional additional headers
        """
        self.client = Client(
            url=url,
            auth_client_secret=auth_client_secret,
            timeout_config=timeout_config,
            additional_headers=additional_headers
        )
    
    def is_connected(self) -> bool:
        """
        Check if the client is connected to Weaviate.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Try to get the schema as a simple health check
            self.client.schema.get()
            return True
        except Exception:
            return False
    
    async def create_schema(self, schema: Dict[str, Any]) -> None:
        """
        Create database schema.
        
        Args:
            schema: Schema definition
        """
        self.client.schema.create(schema)
    
    async def delete_schema(self) -> None:
        """Delete database schema."""
        self.client.schema.delete_all()
    
    async def create_object(
        self,
        class_name: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None
    ) -> str:
        """
        Create a new object.
        
        Args:
            class_name: Class name
            properties: Object properties
            vector: Optional vector for the object
            
        Returns:
            str: Object ID
        """
        return self.client.data_object.create(
            class_name=class_name,
            properties=properties,
            vector=vector
        )
    
    async def get_object(
        self,
        class_name: str,
        object_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get an object by ID.
        
        Args:
            class_name: Class name
            object_id: Object ID
            
        Returns:
            Optional[Dict[str, Any]]: Object if found
        """
        try:
            return self.client.data_object.get_by_id(
                class_name=class_name,
                uuid=object_id
            )
        except Exception:
            return None
    
    async def update_object(
        self,
        class_name: str,
        object_id: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None
    ) -> None:
        """
        Update an object.
        
        Args:
            class_name: Class name
            object_id: Object ID
            properties: New properties
            vector: Optional new vector
        """
        self.client.data_object.update(
            class_name=class_name,
            uuid=object_id,
            properties=properties,
            vector=vector
        )
    
    async def delete_object(
        self,
        class_name: str,
        object_id: str
    ) -> None:
        """
        Delete an object.
        
        Args:
            class_name: Class name
            object_id: Object ID
        """
        self.client.data_object.delete(
            class_name=class_name,
            uuid=object_id
        )
    
    async def search(
        self,
        query: SearchQuery
    ) -> List[Dict[str, Any]]:
        """
        Search for objects.
        
        Args:
            query: Search query
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        # Build Weaviate query
        weaviate_query = (
            self.client.query
            .get(query.class_name)
            .with_additional(["vector", "distance"])
        )
        
        # Add text search if specified
        if query.text:
            weaviate_query = weaviate_query.with_near_text({
                "concepts": [query.text]
            })
        
        # Add vector search if specified
        if query.vector:
            weaviate_query = weaviate_query.with_near_vector({
                "vector": query.vector
            })
        
        # Add filters if specified
        if query.filters:
            weaviate_query = weaviate_query.with_where(query.filters)
        
        # Add limit and offset
        weaviate_query = (
            weaviate_query
            .with_limit(query.limit)
            .with_offset(query.offset)
        )
        
        # Execute query
        result = weaviate_query.do()
        
        # Extract results
        return result["data"]["Get"][query.class_name]
    
    async def batch_create(
        self,
        class_name: str,
        objects: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Create multiple objects in batch.
        
        Args:
            class_name: Class name
            objects: List of objects to create
            
        Returns:
            List[str]: List of created object IDs
        """
        with self.client.batch as batch:
            batch.batch_size = 100
            object_ids = []
            
            for obj in objects:
                object_id = generate_uuid5(obj)
                batch.add_data_object(
                    class_name=class_name,
                    data_object=obj,
                    uuid=object_id
                )
                object_ids.append(object_id)
            
            return object_ids
    
    async def batch_delete(
        self,
        class_name: str,
        object_ids: List[str]
    ) -> None:
        """
        Delete multiple objects in batch.
        
        Args:
            class_name: Class name
            object_ids: List of object IDs to delete
        """
        with self.client.batch as batch:
            batch.batch_size = 100
            
            for object_id in object_ids:
                batch.delete_data_object(
                    class_name=class_name,
                    uuid=object_id
                )
    
    async def close(self) -> None:
        """Close the client connection."""
        self.client.close() 