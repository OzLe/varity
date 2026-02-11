"""
Command and query handlers for search operations.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ...core.entities import (
    SearchQuery,
    SearchResult,
    SearchResponse
)
from ..services.search_application_service import SearchApplicationService


@dataclass
class SearchQuery:
    """Query to search documents."""
    query: SearchQuery
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GetDocumentQuery:
    """Query to get a document by ID."""
    document_id: str
    metadata: Optional[Dict[str, Any]] = None


class SearchHandler:
    """
    Handler for search commands and queries.
    
    This class processes commands and queries by delegating to the
    application service.
    """
    
    def __init__(self, service: SearchApplicationService):
        """
        Initialize the handler.
        
        Args:
            service: Search application service
        """
        self.service = service
    
    async def handle_search(
        self,
        query: SearchQuery
    ) -> SearchResponse:
        """
        Handle search query.
        
        Args:
            query: Search query
            
        Returns:
            SearchResponse: Search results
        """
        return await self.service.search(
            query.query,
            query.metadata
        )
    
    async def handle_get_document(
        self,
        query: GetDocumentQuery
    ) -> Optional[SearchResult]:
        """
        Handle get document query.
        
        Args:
            query: Get document query
            
        Returns:
            Optional[SearchResult]: Document if found
        """
        return await self.service.get_document(
            query.document_id,
            query.metadata
        ) 