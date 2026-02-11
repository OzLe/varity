"""
Search commands for CLI.

This module provides command handlers for document search operations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ...cli.handlers.cli_handler import CommandHandler, CommandResult
from ...cli.formatters.output_formatter import OutputFormatter
from ....application.services.search_application_service import SearchApplicationService
from ....domain.search.search_domain_service import SearchDomainService
from ....infrastructure.database.factory import DatabaseFactory


class SearchCommand(CommandHandler):
    """
    Command handler for document search.
    
    This handler performs semantic search on documents
    using a query string.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        search_service: Optional[SearchApplicationService] = None
    ):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
            search_service: Optional search service
        """
        super().__init__(formatter)
        self.search_service = search_service or SearchApplicationService(
            SearchDomainService(),
            DatabaseFactory.create_database()
        )
    
    async def execute(
        self,
        query: str,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> CommandResult:
        """
        Execute the search command.
        
        Args:
            query: Search query
            limit: Optional result limit
            filters: Optional search filters
            **kwargs: Additional arguments
            
        Returns:
            CommandResult: Command execution result
        """
        try:
            # Validate query
            if not query.strip():
                return self.handle_error(
                    ValueError("Empty search query"),
                    "Invalid query"
                )
            
            # Perform search
            results = await self.search_service.search_documents(
                query,
                limit=limit,
                filters=filters
            )
            
            # Format results
            if not results:
                return self.handle_success(
                    "No results found",
                    data=[]
                )
            
            # Format result data
            formatted_results = [
                {
                    "ID": doc.id,
                    "Title": doc.title,
                    "Score": f"{doc.score:.2f}",
                    "Created": self.formatter.format_timestamp(
                        datetime.fromisoformat(doc.created_at)
                    ),
                    "Updated": self.formatter.format_timestamp(
                        datetime.fromisoformat(doc.updated_at)
                    )
                }
                for doc in results
            ]
            
            return self.handle_success(
                "Search completed successfully",
                data=formatted_results,
                details=f"Found {len(results)} results"
            )
        
        except Exception as e:
            return self.handle_error(e, "Search failed")


class FilterCommand(CommandHandler):
    """
    Command handler for document filtering.
    
    This handler retrieves documents based on filters
    without performing a semantic search.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        search_service: Optional[SearchApplicationService] = None
    ):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
            search_service: Optional search service
        """
        super().__init__(formatter)
        self.search_service = search_service or SearchApplicationService(
            SearchDomainService(),
            DatabaseFactory.create_database()
        )
    
    async def execute(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        **kwargs
    ) -> CommandResult:
        """
        Execute the filter command.
        
        Args:
            filters: Search filters
            limit: Optional result limit
            **kwargs: Additional arguments
            
        Returns:
            CommandResult: Command execution result
        """
        try:
            # Validate filters
            if not filters:
                return self.handle_error(
                    ValueError("No filters provided"),
                    "Invalid filters"
                )
            
            # Get filtered documents
            results = await self.search_service.get_filtered_documents(
                filters,
                limit=limit
            )
            
            # Format results
            if not results:
                return self.handle_success(
                    "No results found",
                    data=[]
                )
            
            # Format result data
            formatted_results = [
                {
                    "ID": doc.id,
                    "Title": doc.title,
                    "Created": self.formatter.format_timestamp(
                        datetime.fromisoformat(doc.created_at)
                    ),
                    "Updated": self.formatter.format_timestamp(
                        datetime.fromisoformat(doc.updated_at)
                    )
                }
                for doc in results
            ]
            
            return self.handle_success(
                "Filter completed successfully",
                data=formatted_results,
                details=f"Found {len(results)} results"
            )
        
        except Exception as e:
            return self.handle_error(e, "Filter failed")


class StatsCommand(CommandHandler):
    """
    Command handler for search statistics.
    
    This handler retrieves statistics about the search
    index and document collection.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        search_service: Optional[SearchApplicationService] = None
    ):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
            search_service: Optional search service
        """
        super().__init__(formatter)
        self.search_service = search_service or SearchApplicationService(
            SearchDomainService(),
            DatabaseFactory.create_database()
        )
    
    async def execute(
        self,
        **kwargs
    ) -> CommandResult:
        """
        Execute the stats command.
        
        Args:
            **kwargs: Additional arguments
            
        Returns:
            CommandResult: Command execution result
        """
        try:
            # Get statistics
            stats = await self.search_service.get_search_stats()
            
            # Format statistics
            formatted_stats = {
                "Total Documents": stats.total_documents,
                "Index Size": f"{stats.index_size_mb:.2f} MB",
                "Last Updated": self.formatter.format_timestamp(
                    datetime.fromisoformat(stats.last_updated)
                ),
                "Average Document Size": f"{stats.avg_document_size_kb:.2f} KB",
                "Index Health": stats.index_health
            }
            
            return self.handle_success(
                "Statistics retrieved successfully",
                data=formatted_stats
            )
        
        except Exception as e:
            return self.handle_error(e, "Failed to retrieve statistics") 