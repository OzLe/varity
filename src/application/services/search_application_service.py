"""
Application service for search operations.

This service orchestrates domain services and handles infrastructure concerns.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ...core.interfaces import (
    RepositoryInterface,
    SearchServiceInterface,
    ClientInterface
)
from ...core.entities import (
    SearchQuery,
    SearchResult,
    SearchResponse
)
from ...domain.search.search_domain_service import SearchDomainService


class SearchApplicationService(SearchServiceInterface):
    """
    Application service for search operations.
    
    This service orchestrates domain services and handles infrastructure concerns.
    """
    
    def __init__(
        self,
        repository: RepositoryInterface,
        client: ClientInterface,
        search_domain_service: SearchDomainService
    ):
        """
        Initialize the service.
        
        Args:
            repository: Document repository
            client: External API client
            search_domain_service: Domain service for search logic
        """
        self.repository = repository
        self.client = client
        self.search_domain_service = search_domain_service
    
    async def search(
        self,
        query: SearchQuery,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SearchResponse:
        """
        Execute a search query.
        
        Args:
            query: Search query
            metadata: Optional search metadata
            
        Returns:
            SearchResponse: Search results
        """
        start_time = datetime.utcnow()
        
        try:
            # Execute search
            raw_results = await self.client.search(query)
            
            # Apply filters if specified
            if query.filters:
                raw_results = self.search_domain_service.filter_results(
                    raw_results,
                    query.filters
                )
            
            # Rank results
            ranked_results = self.search_domain_service.rank_results(
                raw_results,
                query
            )
            
            # Convert to domain objects
            results = [
                self.search_domain_service.create_search_result(
                    uri=r.get('uri', ''),
                    title=r.get('title', ''),
                    description=r.get('description'),
                    score=r.get('score', 0.0),
                    type=r.get('type', ''),
                    metadata=r.get('metadata', {}),
                    highlights=r.get('highlights', [])
                )
                for r in ranked_results
            ]
            
            # Calculate query time
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create response
            return self.search_domain_service.create_search_response(
                results=results,
                total_results=len(results),
                query_time_ms=query_time,
                query=query,
                metadata=metadata
            )
            
        except Exception as e:
            # Handle errors
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return self.search_domain_service.create_search_response(
                results=[],
                total_results=0,
                query_time_ms=query_time,
                query=query,
                metadata={
                    'error': str(e),
                    'status': 'error'
                }
            )
    
    async def get_document(
        self,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SearchResult]:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            metadata: Optional metadata
            
        Returns:
            Optional[SearchResult]: Document if found
        """
        try:
            # Get document
            document = await self.repository.get_document(document_id)
            if not document:
                return None
            
            # Convert to search result
            return self.search_domain_service.create_search_result(
                uri=document.uri,
                title=document.title,
                description=document.description,
                type=document.type,
                metadata=document.metadata
            )
            
        except Exception as e:
            # Log error and return None
            if metadata and 'logger' in metadata:
                metadata['logger'].error(f"Error getting document {document_id}: {str(e)}")
            return None

SearchService = SearchApplicationService 