"""
Weaviate implementation of the document repository.

This module provides a Weaviate-specific implementation of the
document repository interface.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .......core.interfaces import RepositoryInterface
from .......core.entities import (
    Document,
    SearchQuery,
    SearchResult
)
from ..weaviate_client import WeaviateClient


class WeaviateDocumentRepository(RepositoryInterface):
    """
    Weaviate implementation of the document repository.
    
    This class implements the document repository interface using
    Weaviate as the underlying database.
    """
    
    CLASS_NAME = "Document"
    
    def __init__(self, client: WeaviateClient):
        """
        Initialize the repository.
        
        Args:
            client: Weaviate client
        """
        self.client = client
    
    async def create_document(
        self,
        document: Document,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new document.
        
        Args:
            document: Document to create
            metadata: Optional creation metadata
            
        Returns:
            str: Document ID
        """
        # Convert document to Weaviate object
        properties = {
            "uri": document.uri,
            "title": document.title,
            "description": document.description,
            "type": document.type,
            "metadata": document.metadata,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Create object
        return await self.client.create_object(
            class_name=self.CLASS_NAME,
            properties=properties,
            vector=document.vector
        )
    
    async def get_document(
        self,
        document_id: str
    ) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Optional[Document]: Document if found
        """
        # Get object
        obj = await self.client.get_object(
            class_name=self.CLASS_NAME,
            object_id=document_id
        )
        
        if not obj:
            return None
        
        # Convert to document
        return Document(
            id=obj["id"],
            uri=obj["properties"]["uri"],
            title=obj["properties"]["title"],
            description=obj["properties"]["description"],
            type=obj["properties"]["type"],
            metadata=obj["properties"]["metadata"],
            vector=obj["vector"] if "vector" in obj else None
        )
    
    async def update_document(
        self,
        document: Document,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update a document.
        
        Args:
            document: Document to update
            metadata: Optional update metadata
        """
        # Convert document to Weaviate object
        properties = {
            "uri": document.uri,
            "title": document.title,
            "description": document.description,
            "type": document.type,
            "metadata": document.metadata,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Update object
        await self.client.update_object(
            class_name=self.CLASS_NAME,
            object_id=document.id,
            properties=properties,
            vector=document.vector
        )
    
    async def delete_document(
        self,
        document_id: str
    ) -> None:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
        """
        await self.client.delete_object(
            class_name=self.CLASS_NAME,
            object_id=document_id
        )
    
    async def search_documents(
        self,
        query: SearchQuery,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for documents.
        
        Args:
            query: Search query
            metadata: Optional search metadata
            
        Returns:
            List[SearchResult]: Search results
        """
        # Execute search
        results = await self.client.search(query)
        
        # Convert to search results
        return [
            SearchResult(
                uri=r["properties"]["uri"],
                title=r["properties"]["title"],
                description=r["properties"]["description"],
                score=r["additional"]["distance"],
                type=r["properties"]["type"],
                metadata=r["properties"]["metadata"],
                highlights=r.get("highlights", [])
            )
            for r in results
        ]
    
    async def batch_create_documents(
        self,
        documents: List[Document],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Create multiple documents in batch.
        
        Args:
            documents: Documents to create
            metadata: Optional creation metadata
            
        Returns:
            List[str]: List of created document IDs
        """
        # Convert documents to Weaviate objects
        objects = [
            {
                "uri": doc.uri,
                "title": doc.title,
                "description": doc.description,
                "type": doc.type,
                "metadata": doc.metadata,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            for doc in documents
        ]
        
        # Create objects in batch
        return await self.client.batch_create(
            class_name=self.CLASS_NAME,
            objects=objects
        )
    
    async def batch_delete_documents(
        self,
        document_ids: List[str]
    ) -> None:
        """
        Delete multiple documents in batch.
        
        Args:
            document_ids: List of document IDs to delete
        """
        await self.client.batch_delete(
            class_name=self.CLASS_NAME,
            object_ids=document_ids
        ) 