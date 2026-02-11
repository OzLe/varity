"""
Data models for document entities.

This module contains the Document class used to represent documents
in the system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import numpy as np


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
    vector: Optional[np.ndarray] = None
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