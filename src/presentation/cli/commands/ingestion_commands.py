"""
Ingestion commands for CLI.

This module provides command handlers for document ingestion operations.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from ...cli.handlers.cli_handler import CommandHandler, CommandResult
from ...cli.formatters.output_formatter import OutputFormatter
from ....application.services.ingestion_application_service import IngestionApplicationService
from ....domain.ingestion.ingestion_domain_service import IngestionDomainService
from ....infrastructure.database.factory import DatabaseFactory


class IngestCommand(CommandHandler):
    """
    Command handler for document ingestion.
    
    This handler processes the ingestion of documents
    from a specified directory.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        ingestion_service: Optional[IngestionApplicationService] = None
    ):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
            ingestion_service: Optional ingestion service
        """
        super().__init__(formatter)
        self.ingestion_service = ingestion_service or IngestionApplicationService(
            IngestionDomainService(),
            DatabaseFactory.create_database()
        )
    
    async def execute(
        self,
        directory: str,
        batch_size: Optional[int] = None,
        **kwargs
    ) -> CommandResult:
        """
        Execute the ingestion command.
        
        Args:
            directory: Directory containing documents
            batch_size: Optional batch size
            **kwargs: Additional arguments
            
        Returns:
            CommandResult: Command execution result
        """
        try:
            # Validate directory
            dir_path = Path(directory)
            if not dir_path.exists():
                return self.handle_error(
                    ValueError(f"Directory not found: {directory}"),
                    "Invalid directory"
                )
            
            # Start ingestion
            self.formatter.print(
                self.formatter.format_progress(
                    "Starting ingestion",
                    0,
                    1
                )
            )
            
            # Process documents
            result = await self.ingestion_service.ingest_documents(
                str(dir_path),
                batch_size=batch_size
            )
            
            # Format result
            if result.success:
                return self.handle_success(
                    "Ingestion completed successfully",
                    data=result,
                    details=f"Processed {result.processed_count} documents"
                )
            else:
                return self.handle_error(
                    result.error or Exception("Unknown error"),
                    "Ingestion failed"
                )
        
        except Exception as e:
            return self.handle_error(e, "Ingestion failed")


class ValidateCommand(CommandHandler):
    """
    Command handler for document validation.
    
    This handler validates documents in a specified directory
    without ingesting them.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        ingestion_service: Optional[IngestionApplicationService] = None
    ):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
            ingestion_service: Optional ingestion service
        """
        super().__init__(formatter)
        self.ingestion_service = ingestion_service or IngestionApplicationService(
            IngestionDomainService(),
            DatabaseFactory.create_database()
        )
    
    async def execute(
        self,
        directory: str,
        **kwargs
    ) -> CommandResult:
        """
        Execute the validation command.
        
        Args:
            directory: Directory containing documents
            **kwargs: Additional arguments
            
        Returns:
            CommandResult: Command execution result
        """
        try:
            # Validate directory
            dir_path = Path(directory)
            if not dir_path.exists():
                return self.handle_error(
                    ValueError(f"Directory not found: {directory}"),
                    "Invalid directory"
                )
            
            # Start validation
            self.formatter.print(
                self.formatter.format_progress(
                    "Starting validation",
                    0,
                    1
                )
            )
            
            # Validate documents
            result = await self.ingestion_service.validate_documents(
                str(dir_path)
            )
            
            # Format result
            if result.success:
                return self.handle_success(
                    "Validation completed successfully",
                    data=result,
                    details=f"Validated {result.processed_count} documents"
                )
            else:
                return self.handle_error(
                    result.error or Exception("Unknown error"),
                    "Validation failed"
                )
        
        except Exception as e:
            return self.handle_error(e, "Validation failed")


class StatusCommand(CommandHandler):
    """
    Command handler for ingestion status.
    
    This handler retrieves the status of document ingestion
    operations.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        ingestion_service: Optional[IngestionApplicationService] = None
    ):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
            ingestion_service: Optional ingestion service
        """
        super().__init__(formatter)
        self.ingestion_service = ingestion_service or IngestionApplicationService(
            IngestionDomainService(),
            DatabaseFactory.create_database()
        )
    
    async def execute(
        self,
        job_id: Optional[str] = None,
        **kwargs
    ) -> CommandResult:
        """
        Execute the status command.
        
        Args:
            job_id: Optional job ID
            **kwargs: Additional arguments
            
        Returns:
            CommandResult: Command execution result
        """
        try:
            # Get status
            if job_id:
                status = await self.ingestion_service.get_job_status(job_id)
            else:
                status = await self.ingestion_service.get_all_job_statuses()
            
            # Format result
            if isinstance(status, list):
                return self.handle_success(
                    "Retrieved all job statuses",
                    data=status,
                    details=f"Found {len(status)} jobs"
                )
            else:
                return self.handle_success(
                    "Retrieved job status",
                    data=status
                )
        
        except Exception as e:
            return self.handle_error(e, "Failed to retrieve status") 