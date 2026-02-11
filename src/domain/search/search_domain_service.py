"""
Domain service for search operations.

This module contains pure business logic for search operations,
separated from infrastructure concerns.
"""

from typing import List, Dict, Any, Optional

from ...core.entities import (
    SearchQuery,
    SearchResult,
    SearchResponse
)


class SearchDomainService:
    """
    Domain service for search operations.
    
    This service contains pure business logic for search, with no
    dependencies on external systems or infrastructure.
    """
    
    @staticmethod
    def create_search_result(
        uri: str,
        title: str,
        description: Optional[str] = None,
        score: float = 0.0,
        type: str = "",
        metadata: Dict[str, Any] = None,
        highlights: List[str] = None
    ) -> SearchResult:
        """
        Create a search result.
        
        Args:
            uri: URI of the result
            title: Title of the result
            description: Optional description
            score: Similarity score
            type: Result type
            metadata: Optional metadata
            highlights: Optional highlight snippets
            
        Returns:
            SearchResult: Search result object
        """
        return SearchResult(
            uri=uri,
            title=title,
            description=description,
            score=score,
            type=type,
            metadata=metadata or {},
            highlights=highlights or []
        )
    
    @staticmethod
    def create_search_response(
        results: List[SearchResult],
        total_results: int,
        query_time_ms: float,
        query: SearchQuery,
        metadata: Dict[str, Any] = None
    ) -> SearchResponse:
        """
        Create a search response.
        
        Args:
            results: List of search results
            total_results: Total number of results
            query_time_ms: Query execution time in milliseconds
            query: Original search query
            metadata: Optional response metadata
            
        Returns:
            SearchResponse: Search response object
        """
        return SearchResponse(
            results=results,
            total_results=total_results,
            query_time_ms=query_time_ms,
            query=query,
            metadata=metadata or {}
        )
    
    @staticmethod
    def normalize_scores(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize similarity scores in results.
        
        Args:
            results: List of result dictionaries with raw scores
            
        Returns:
            List[Dict[str, Any]]: Results with normalized scores
        """
        if not results:
            return results
        
        # Extract scores
        scores = [r.get('score', 0.0) for r in results]
        
        # Find min and max for normalization
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
        
        # Normalize scores
        normalized_results = []
        for result in results:
            normalized_result = result.copy()
            if score_range > 0:
                normalized_result['score'] = (result.get('score', 0.0) - min_score) / score_range
            else:
                normalized_result['score'] = 1.0
            normalized_results.append(normalized_result)
        
        return normalized_results
    
    @staticmethod
    def rank_results(
        results: List[Dict[str, Any]],
        query: SearchQuery
    ) -> List[Dict[str, Any]]:
        """
        Rank search results based on query parameters.
        
        Args:
            results: List of result dictionaries
            query: Search query with ranking parameters
            
        Returns:
            List[Dict[str, Any]]: Ranked results
        """
        # Normalize scores
        normalized_results = SearchDomainService.normalize_scores(results)
        
        # Apply sorting if specified
        if query.sort_by:
            normalized_results.sort(
                key=lambda x: x.get(query.sort_by, 0.0),
                reverse=(query.sort_order.lower() == 'desc')
            )
        
        return normalized_results
    
    @staticmethod
    def filter_results(
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter search results based on criteria.
        
        Args:
            results: List of result dictionaries
            filters: Filter criteria
            
        Returns:
            List[Dict[str, Any]]: Filtered results
        """
        if not filters:
            return results
        
        filtered_results = []
        for result in results:
            matches = True
            for key, value in filters.items():
                if key not in result or result[key] != value:
                    matches = False
                    break
            if matches:
                filtered_results.append(result)
        
        return filtered_results 