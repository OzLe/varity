"""
Command and query handlers for ingestion operations.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ...core.entities import (
    Document,
    ProcessingStatus
)
from ..services.ingestion_application_service import IngestionApplicationService


@dataclass
class ProcessDocumentCommand:
    """Command to process a document."""
    document: Document
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GetProcessingStatusQuery:
    """Query to get document processing status."""
    document_id: str


@dataclass
class RetryProcessingCommand:
    """Command to retry processing a document."""
    document_id: str
    metadata: Optional[Dict[str, Any]] = None


class IngestionHandler:
    """
    Handler for ingestion commands and queries.
    
    This class processes commands and queries by delegating to the
    application service.
    """
    
    def __init__(self, service: IngestionApplicationService):
        """
        Initialize the handler.
        
        Args:
            service: Ingestion application service
        """
        self.service = service
    
    async def handle_process_document(
        self,
        command: ProcessDocumentCommand
    ) -> ProcessingStatus:
        """
        Handle process document command.
        
        Args:
            command: Process document command
            
        Returns:
            ProcessingStatus: Processing status
        """
        return await self.service.process_document(
            command.document,
            command.metadata
        )
    
    async def handle_get_processing_status(
        self,
        query: GetProcessingStatusQuery
    ) -> ProcessingStatus:
        """
        Handle get processing status query.
        
        Args:
            query: Get processing status query
            
        Returns:
            ProcessingStatus: Processing status
        """
        return await self.service.get_processing_status(query.document_id)
    
    async def handle_retry_processing(
        self,
        command: RetryProcessingCommand
    ) -> ProcessingStatus:
        """
        Handle retry processing command.
        
        Args:
            command: Retry processing command
            
        Returns:
            ProcessingStatus: Processing status
        """
        return await self.service.retry_processing(
            command.document_id,
            command.metadata
        ) 