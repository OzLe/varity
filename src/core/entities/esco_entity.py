"""
Base ESCO entity class that defines common attributes and methods for all ESCO entities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class ESCOEntity:
    """
    Base class for all ESCO entities.
    
    This class defines common attributes and methods that are shared across
    all ESCO entity types (Occupations, Skills, ISCO Groups, etc.).
    """
    uri: str
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    alt_labels: List[str] = field(default_factory=list)
    hidden_labels: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        return {
            'uri': self.uri,
            'code': self.code,
            'title': self.title,
            'description': self.description,
            'alt_labels': self.alt_labels,
            'hidden_labels': self.hidden_labels,
            'properties': self.properties,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ESCOEntity':
        """Create entity from dictionary representation."""
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        
        return cls(
            uri=data['uri'],
            code=data.get('code'),
            title=data.get('title'),
            description=data.get('description'),
            alt_labels=data.get('alt_labels', []),
            hidden_labels=data.get('hidden_labels', []),
            properties=data.get('properties', {}),
            created_at=created_at,
            updated_at=updated_at
        ) 