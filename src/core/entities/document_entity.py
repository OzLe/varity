"""
Data models for document entities.

This module contains the Document class used to represent documents
in the system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class Document:
    """
    Represents a document in the system.
    
    This class contains all the information about a document,
    including its content, metadata, and vector representation.
    """
    id: str
    uri: str
    title: str
    description: Optional[str] = None
    type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary representation."""
        return {
            'id': self.id,
            'uri': self.uri,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class TranslationRequest:
    """Request for text translation."""
    text: str
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TranslationResponse:
    """Response from text translation."""
    text: str
    source_lang: str = ""
    target_lang: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingRequest:
    """Request for text embedding."""
    text: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResponse:
    """Response from text embedding."""
    text: str
    embedding: List[float] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None 