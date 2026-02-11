"""
Application service for ingestion operations.

This service orchestrates domain services and handles infrastructure concerns.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ...core.interfaces import (
    RepositoryInterface,
    IngestionServiceInterface,
    VectorDatabaseClientInterface
)
from ...core.entities import (
    Document,
    ValidationResult,
    IngestionDecision,
    ProcessingStatus
)
from ...domain.ingestion.ingestion_domain_service import IngestionDomainService
from ...domain.ingestion.state_management_service import StateManagementService


class IngestionApplicationService(IngestionServiceInterface):
    """
    Application service for ingestion operations.
    
    This service orchestrates domain services and handles infrastructure concerns.
    """
    
    def __init__(
        self,
        repository: RepositoryInterface,
        client: VectorDatabaseClientInterface,
        ingestion_domain_service: IngestionDomainService,
        state_management_service: StateManagementService
    ):
        """
        Initialize the service.
        
        Args:
            repository: Document repository
            client: External API client
            ingestion_domain_service: Domain service for ingestion logic
            state_management_service: Domain service for state management
        """
        self.repository = repository
        self.client = client
        self.ingestion_domain_service = ingestion_domain_service
        self.state_management_service = state_management_service
    
    async def process_document(
        self,
        document: Document,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingStatus:
        """
        Process a document through the ingestion pipeline.
        
        Args:
            document: Document to process
            metadata: Optional processing metadata
            
        Returns:
            ProcessingStatus: Processing status
        """
        # Validate document
        validation_result = await self.ingestion_domain_service.validate_document(
            document,
            metadata
        )
        
        if not validation_result.is_valid:
            return ProcessingStatus(
                document_id=document.id,
                status="failed",
                error=validation_result.error,
                timestamp=datetime.utcnow()
            )
        
        # Make ingestion decision
        decision = await self.ingestion_domain_service.decide_ingestion(
            document,
            validation_result,
            metadata
        )
        
        if decision.action == "reject":
            return ProcessingStatus(
                document_id=document.id,
                status="rejected",
                reason=decision.reason,
                timestamp=datetime.utcnow()
            )
        
        # Update processing state
        await self.state_management_service.update_processing_state(
            document.id,
            "processing",
            metadata
        )
        
        try:
            # Process document based on decision
            if decision.action == "process":
                await self.ingestion_domain_service.process_document(
                    document,
                    decision,
                    metadata
                )
            elif decision.action == "transform":
                await self.ingestion_domain_service.transform_document(
                    document,
                    decision,
                    metadata
                )
            
            # Update final state
            await self.state_management_service.update_processing_state(
                document.id,
                "completed",
                metadata
            )
            
            return ProcessingStatus(
                document_id=document.id,
                status="completed",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            # Update error state
            await self.state_management_service.update_processing_state(
                document.id,
                "failed",
                {"error": str(e)}
            )
            
            return ProcessingStatus(
                document_id=document.id,
                status="failed",
                error=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def get_processing_status(
        self,
        document_id: str
    ) -> ProcessingStatus:
        """
        Get the processing status of a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            ProcessingStatus: Current processing status
        """
        return await self.state_management_service.get_processing_state(document_id)
    
    async def retry_processing(
        self,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingStatus:
        """
        Retry processing a failed document.
        
        Args:
            document_id: Document ID
            metadata: Optional processing metadata
            
        Returns:
            ProcessingStatus: New processing status
        """
        # Get document
        document = await self.repository.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Reset processing state
        await self.state_management_service.update_processing_state(
            document_id,
            "pending",
            metadata
        )
        
        # Process document
        return await self.process_document(document, metadata)

IngestionService = IngestionApplicationService 