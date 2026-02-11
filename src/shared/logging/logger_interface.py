"""
Logger interface for standardized logging across the application.

This module defines the interface for logging implementations,
ensuring consistent logging behavior across the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Standard log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggerInterface(ABC):
    """
    Interface for logging implementations.
    
    This abstract class defines the contract that all logging
    implementations must follow to ensure consistent logging
    behavior across the application.
    """
    
    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log a debug message.
        
        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log an info message.
        
        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """
        Log a warning message.
        
        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """
        Log an error message.
        
        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs: Any) -> None:
        """
        Log a critical message.
        
        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass
    
    @abstractmethod
    def exception(self, message: str, exc_info: Optional[Exception] = None, **kwargs: Any) -> None:
        """
        Log an exception.
        
        Args:
            message: The message to log
            exc_info: Optional exception to log
            **kwargs: Additional context data
        """
        pass
    
    @abstractmethod
    def set_level(self, level: LogLevel) -> None:
        """
        Set the logging level.
        
        Args:
            level: The log level to set
        """
        pass
    
    @abstractmethod
    def get_level(self) -> LogLevel:
        """
        Get the current logging level.
        
        Returns:
            LogLevel: The current log level
        """
        pass
    
    @abstractmethod
    def add_context(self, **kwargs: Any) -> None:
        """
        Add context data to all subsequent log messages.
        
        Args:
            **kwargs: Context data to add
        """
        pass
    
    @abstractmethod
    def clear_context(self) -> None:
        """Clear all context data."""
        pass
    
    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        """
        Get the current context data.
        
        Returns:
            Dict[str, Any]: Current context data
        """
        pass 