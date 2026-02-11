"""
Log formatter for consistent message formatting.

This module provides utilities for formatting log messages
in a consistent way across the application.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class LogFormatter:
    """
    Log formatter for consistent message formatting.
    
    This class provides methods for formatting log messages
    and their context in a consistent way.
    """
    
    @staticmethod
    def format_message(
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Format a log message with context.
        
        Args:
            message: The message to format
            context: Optional context data
            timestamp: Optional timestamp
            
        Returns:
            str: Formatted message
        """
        # Start with timestamp if provided
        parts = []
        if timestamp:
            parts.append(f"[{timestamp.isoformat()}]")
        
        # Add message
        parts.append(message)
        
        # Add context if provided
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            parts.append(f"({context_str})")
        
        return " ".join(parts)
    
    @staticmethod
    def format_error(
        error: Exception,
        include_traceback: bool = True
    ) -> Dict[str, Any]:
        """
        Format an error for logging.
        
        Args:
            error: The error to format
            include_traceback: Whether to include traceback
            
        Returns:
            Dict[str, Any]: Formatted error
        """
        formatted = {
            "type": error.__class__.__name__,
            "message": str(error)
        }
        
        if include_traceback:
            import traceback
            formatted["traceback"] = traceback.format_exception(
                type(error),
                error,
                error.__traceback__
            )
        
        return formatted
    
    @staticmethod
    def format_context(
        context: Dict[str, Any],
        exclude_keys: Optional[set] = None
    ) -> Dict[str, Any]:
        """
        Format context data for logging.
        
        Args:
            context: Context data to format
            exclude_keys: Optional set of keys to exclude
            
        Returns:
            Dict[str, Any]: Formatted context
        """
        if not exclude_keys:
            exclude_keys = set()
        
        return {
            k: v for k, v in context.items()
            if k not in exclude_keys
        }
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format a duration in seconds.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            str: Formatted duration
        """
        if seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.2f}h"
    
    @staticmethod
    def format_size(bytes_: int) -> str:
        """
        Format a size in bytes.
        
        Args:
            bytes_: Size in bytes
            
        Returns:
            str: Formatted size
        """
        if bytes_ < 1024:
            return f"{bytes_}B"
        elif bytes_ < 1024 * 1024:
            kb = bytes_ / 1024
            return f"{kb:.2f}KB"
        elif bytes_ < 1024 * 1024 * 1024:
            mb = bytes_ / (1024 * 1024)
            return f"{mb:.2f}MB"
        else:
            gb = bytes_ / (1024 * 1024 * 1024)
            return f"{gb:.2f}GB" 