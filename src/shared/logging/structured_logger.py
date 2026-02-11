"""
Structured logger implementation.

This module provides a structured logging implementation that
formats log messages in a consistent, machine-readable format.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, TextIO

from .logger_interface import LoggerInterface, LogLevel


class StructuredLogger(LoggerInterface):
    """
    Structured logger implementation.
    
    This class implements the LoggerInterface to provide
    structured logging capabilities with consistent formatting
    and context management.
    """
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        output: TextIO = sys.stdout
    ):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name
            level: Initial log level
            output: Output stream for logs
        """
        self.name = name
        self._level = level
        self._output = output
        self._context: Dict[str, Any] = {}
        
        # Set up Python's logging
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level.value)
        
        # Create handler
        handler = logging.StreamHandler(output)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: Optional[Exception] = None,
        **kwargs: Any
    ) -> None:
        """
        Internal logging method.
        
        Args:
            level: Log level
            message: Message to log
            exc_info: Optional exception
            **kwargs: Additional context
        """
        if level.value < self._level.value:
            return
        
        # Prepare log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "logger": self.name,
            "message": message,
            "context": {**self._context, **kwargs}
        }
        
        # Add exception info if present
        if exc_info:
            log_entry["exception"] = {
                "type": exc_info.__class__.__name__,
                "message": str(exc_info),
                "traceback": traceback.format_exception(
                    type(exc_info),
                    exc_info,
                    exc_info.__traceback__
                )
            }
        
        # Log the entry
        self._logger.log(
            getattr(logging, level.value),
            json.dumps(log_entry)
        )
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, exc_info: Optional[Exception] = None, **kwargs: Any) -> None:
        """Log an exception."""
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **kwargs)
    
    def set_level(self, level: LogLevel) -> None:
        """Set the logging level."""
        self._level = level
        self._logger.setLevel(level.value)
    
    def get_level(self) -> LogLevel:
        """Get the current logging level."""
        return self._level
    
    def add_context(self, **kwargs: Any) -> None:
        """Add context data."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context data."""
        self._context.clear()
    
    def get_context(self) -> Dict[str, Any]:
        """Get the current context data."""
        return self._context.copy()

def configure_logging(name: str = "varity", level: LogLevel = LogLevel.INFO, output: TextIO = sys.stdout) -> StructuredLogger:
    """
    Configure and return a StructuredLogger instance.
    Args:
        name: Logger name
        level: Logging level
        output: Output stream for logs
    Returns:
        StructuredLogger: Configured logger instance
    """
    return StructuredLogger(name=name, level=level, output=output) 