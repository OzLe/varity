"""
Ingestion container for document processing.

This module provides a container for document ingestion operations,
including initialization, health checks, and graceful shutdown.
"""

import asyncio
import signal
from typing import Optional, Dict, Any
from pathlib import Path

from ...application.services.ingestion_service import IngestionService
from ...domain.ingestion.ingestion_domain_service import IngestionDomainService
from ...infrastructure.database.factory import DatabaseFactory
from ...infrastructure.config.config_manager import ConfigManager
from .health_check import HealthChecker, HealthMonitor


class IngestionContainer:
    """
    Container for document ingestion operations.
    
    This class manages the lifecycle of ingestion operations,
    including initialization, health checks, and graceful shutdown.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        environment: Optional[str] = None
    ):
        """
        Initialize the container.
        
        Args:
            config_path: Optional path to configuration file
            environment: Optional environment name
        """
        # Initialize configuration
        self.config_manager = ConfigManager(
            config_dir=config_path,
            environment=environment
        )
        
        # Initialize services
        self.database_factory = DatabaseFactory()
        self.ingestion_service = IngestionService(
            IngestionDomainService(),
            self.database_factory.create_database()
        )
        
        # Initialize health monitoring
        self.health_checker = HealthChecker(
            self.config_manager,
            self.database_factory
        )
        self.health_monitor = HealthMonitor(self.health_checker)
        
        # Set up signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown())
            )
    
    async def start(self) -> None:
        """Start the container."""
        try:
            # Start health monitoring
            await self.health_monitor.start_monitoring()
            
            # Initialize database
            await self.ingestion_service.initialize()
            
            print("Ingestion container started successfully")
            
            # Keep container running
            while True:
                await asyncio.sleep(1)
        
        except Exception as e:
            print(f"Error starting container: {str(e)}")
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the container gracefully."""
        try:
            print("Shutting down ingestion container...")
            
            # Stop health monitoring
            self.health_monitor.stop_monitoring()
            
            # Close services
            await self.ingestion_service.close()
            
            print("Ingestion container shut down successfully")
            
            # Stop event loop
            loop = asyncio.get_event_loop()
            loop.stop()
        
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")
    
    async def process_directory(
        self,
        directory: str,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process documents in a directory.
        
        Args:
            directory: Directory containing documents
            batch_size: Optional batch size
            
        Returns:
            Dict[str, Any]: Processing result
        """
        try:
            # Validate directory
            dir_path = Path(directory)
            if not dir_path.exists():
                raise ValueError(f"Directory not found: {directory}")
            
            # Process documents
            result = await self.ingestion_service.ingest_documents(
                str(dir_path),
                batch_size=batch_size
            )
            
            return {
                "success": result.success,
                "processed_count": result.processed_count,
                "errors": result.errors,
                "warnings": result.warnings
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_directory(
        self,
        directory: str
    ) -> Dict[str, Any]:
        """
        Validate documents in a directory.
        
        Args:
            directory: Directory containing documents
            
        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            # Validate directory
            dir_path = Path(directory)
            if not dir_path.exists():
                raise ValueError(f"Directory not found: {directory}")
            
            # Validate documents
            result = await self.ingestion_service.validate_documents(
                str(dir_path)
            )
            
            return {
                "success": result.success,
                "processed_count": result.processed_count,
                "errors": result.errors,
                "warnings": result.warnings
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_status(
        self,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get ingestion status.
        
        Args:
            job_id: Optional job ID
            
        Returns:
            Dict[str, Any]: Status information
        """
        try:
            if job_id:
                status = await self.ingestion_service.get_job_status(job_id)
            else:
                status = await self.ingestion_service.get_all_job_statuses()
            
            return {
                "success": True,
                "status": status
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current health status.
        
        Returns:
            Optional[Dict[str, Any]]: Health status
        """
        status = self.health_monitor.get_last_status()
        if status:
            return {
                "status": status.status,
                "timestamp": status.timestamp.isoformat(),
                "details": status.details,
                "errors": status.errors
            }
        return None 