"""
Data models for the Varity search functionality.

This module contains all data classes used to represent search queries,
results, and related metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class SearchQuery:
    """
    Represents a search query with all its parameters.
    
    This class encapsulates all the parameters that can be used to
    customize a search operation.
    """
    query_text: str
    limit: int = 10
    offset: int = 0
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    include_metadata: bool = True
    search_fields: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary representation."""
        return {
            'query_text': self.query_text,
            'limit': self.limit,
            'offset': self.offset,
            'filters': self.filters,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'include_metadata': self.include_metadata,
            'search_fields': self.search_fields
        }


@dataclass
class SearchResult:
    """
    Represents a single search result item.
    
    This class contains all the information about a single result
    returned from a search operation.
    """
    uri: str
    title: str
    description: Optional[str] = None
    score: float = 0.0
    type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            'uri': self.uri,
            'title': self.title,
            'description': self.description,
            'score': self.score,
            'type': self.type,
            'metadata': self.metadata,
            'highlights': self.highlights
        }


@dataclass
class SearchResponse:
    """
    Represents the complete response from a search operation.
    
    This class contains the list of results along with metadata about
    the search operation itself.
    """
    results: List[SearchResult]
    total_results: int
    query_time_ms: float
    query: SearchQuery
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary representation."""
        return {
            'results': [result.to_dict() for result in self.results],
            'total_results': self.total_results,
            'query_time_ms': self.query_time_ms,
            'query': self.query.to_dict(),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        } 