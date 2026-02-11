"""
Output formatter for CLI commands.

This module provides consistent formatting for CLI output,
including tables, JSON, and text formatting.
"""

from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime
from tabulate import tabulate
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class OutputFormatter:
    """
    Formatter for CLI command output.
    
    This class provides methods for formatting different types of output
    in a consistent and reusable way.
    """
    
    def __init__(self, use_rich: bool = True):
        """
        Initialize the formatter.
        
        Args:
            use_rich: Whether to use rich formatting
        """
        self.use_rich = use_rich
        self.console = Console() if use_rich else None
    
    def format_table(
        self,
        data: List[Dict[str, Any]],
        headers: Optional[List[str]] = None,
        title: Optional[str] = None
    ) -> str:
        """
        Format data as a table.
        
        Args:
            data: List of dictionaries containing row data
            headers: Optional list of header names
            title: Optional table title
            
        Returns:
            str: Formatted table
        """
        if not data:
            return "No data to display"
        
        if self.use_rich:
            table = Table(title=title) if title else Table()
            
            # Add headers
            if headers:
                for header in headers:
                    table.add_column(header)
            else:
                for key in data[0].keys():
                    table.add_column(key)
            
            # Add rows
            for row in data:
                table.add_row(*[str(row.get(key, "")) for key in (headers or row.keys())])
            
            return table
        else:
            if headers:
                return tabulate(
                    [[row.get(key, "") for key in headers] for row in data],
                    headers=headers,
                    tablefmt="grid"
                )
            return tabulate(data, headers="keys", tablefmt="grid")
    
    def format_json(
        self,
        data: Union[Dict[str, Any], List[Any]],
        pretty: bool = True
    ) -> str:
        """
        Format data as JSON.
        
        Args:
            data: Data to format
            pretty: Whether to pretty print
            
        Returns:
            str: Formatted JSON
        """
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)
    
    def format_error(
        self,
        message: str,
        details: Optional[str] = None
    ) -> str:
        """
        Format error message.
        
        Args:
            message: Error message
            details: Optional error details
            
        Returns:
            str: Formatted error
        """
        if self.use_rich:
            error_text = Text(message, style="bold red")
            if details:
                error_text.append("\n" + details, style="red")
            return Panel(error_text, title="Error", border_style="red")
        else:
            if details:
                return f"Error: {message}\n{details}"
            return f"Error: {message}"
    
    def format_success(
        self,
        message: str,
        details: Optional[str] = None
    ) -> str:
        """
        Format success message.
        
        Args:
            message: Success message
            details: Optional success details
            
        Returns:
            str: Formatted success message
        """
        if self.use_rich:
            success_text = Text(message, style="bold green")
            if details:
                success_text.append("\n" + details, style="green")
            return Panel(success_text, title="Success", border_style="green")
        else:
            if details:
                return f"Success: {message}\n{details}"
            return f"Success: {message}"
    
    def format_progress(
        self,
        message: str,
        current: int,
        total: int
    ) -> str:
        """
        Format progress message.
        
        Args:
            message: Progress message
            current: Current progress
            total: Total progress
            
        Returns:
            str: Formatted progress message
        """
        if self.use_rich:
            return f"{message} [{current}/{total}]"
        return f"{message} [{current}/{total}]"
    
    def format_timestamp(
        self,
        timestamp: datetime,
        format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> str:
        """
        Format timestamp.
        
        Args:
            timestamp: Timestamp to format
            format_str: Format string
            
        Returns:
            str: Formatted timestamp
        """
        return timestamp.strftime(format_str)
    
    def print(
        self,
        content: Any,
        style: Optional[str] = None
    ) -> None:
        """
        Print content with optional styling.
        
        Args:
            content: Content to print
            style: Optional style
        """
        if self.use_rich:
            if style:
                self.console.print(content, style=style)
            else:
                self.console.print(content)
        else:
            print(content) 