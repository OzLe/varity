"""
Search container for document search operations.

This module provides a container for document search operations,
including initialization, health checks, and graceful shutdown.
"""

import asyncio
import signal
from typing import Optional, Dict, Any, List

from ...application.services.search_service import SearchService
from ...domain.search.search_domain_service import SearchDomainService
from ...infrastructure.database.factory import DatabaseFactory
from ...infrastructure.config.config_manager import ConfigManager
from .health_check import HealthChecker, HealthMonitor


class SearchContainer:
    """
    Container for document search operations.
    
    This class manages the lifecycle of search operations,
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
        self.search_service = SearchService(
            SearchDomainService(),
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
            await self.search_service.initialize()
            
            print("Search container started successfully")
            
            # Keep container running
            while True:
                await asyncio.sleep(1)
        
        except Exception as e:
            print(f"Error starting container: {str(e)}")
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the container gracefully."""
        try:
            print("Shutting down search container...")
            
            # Stop health monitoring
            self.health_monitor.stop_monitoring()
            
            # Close services
            await self.search_service.close()
            
            print("Search container shut down successfully")
            
            # Stop event loop
            loop = asyncio.get_event_loop()
            loop.stop()
        
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")
    
    async def search_documents(
        self,
        query: str,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search documents.
        
        Args:
            query: Search query
            limit: Optional result limit
            filters: Optional search filters
            
        Returns:
            Dict[str, Any]: Search results
        """
        try:
            # Validate query
            if not query.strip():
                raise ValueError("Empty search query")
            
            # Perform search
            results = await self.search_service.search_documents(
                query,
                limit=limit,
                filters=filters
            )
            
            return {
                "success": True,
                "results": [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "score": doc.score,
                        "created_at": doc.created_at,
                        "updated_at": doc.updated_at
                    }
                    for doc in results
                ]
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def filter_documents(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Filter documents.
        
        Args:
            filters: Search filters
            limit: Optional result limit
            
        Returns:
            Dict[str, Any]: Filter results
        """
        try:
            # Validate filters
            if not filters:
                raise ValueError("No filters provided")
            
            # Get filtered documents
            results = await self.search_service.get_filtered_documents(
                filters,
                limit=limit
            )
            
            return {
                "success": True,
                "results": [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "created_at": doc.created_at,
                        "updated_at": doc.updated_at
                    }
                    for doc in results
                ]
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get search statistics.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            stats = await self.search_service.get_search_stats()
            
            return {
                "success": True,
                "stats": {
                    "total_documents": stats.total_documents,
                    "index_size_mb": stats.index_size_mb,
                    "last_updated": stats.last_updated,
                    "avg_document_size_kb": stats.avg_document_size_kb,
                    "index_health": stats.index_health
                }
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