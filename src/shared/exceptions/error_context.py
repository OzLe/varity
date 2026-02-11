"""
Error context management system.

This module provides utilities for managing error context and
structured error information across the application.
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class ErrorContext:
    """
    Structured error context information.
    
    This class provides a standardized way to capture and manage
    error context information across the application.
    """
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[List[str]] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error context to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "context_data": self.context_data,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "recovery_strategy": self.recovery_strategy
        }
    
    def add_context(self, **kwargs: Any) -> None:
        """
        Add context data.
        
        Args:
            **kwargs: Context data to add
        """
        self.context_data.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context data."""
        self.context_data.clear()
    
    def set_recovery_status(
        self,
        attempted: bool,
        successful: bool,
        strategy: Optional[str] = None
    ) -> None:
        """
        Set recovery status.
        
        Args:
            attempted: Whether recovery was attempted
            successful: Whether recovery was successful
            strategy: Optional recovery strategy name
        """
        self.recovery_attempted = attempted
        self.recovery_successful = successful
        self.recovery_strategy = strategy


class ErrorContextManager:
    """
    Manager for error context information.
    
    This class provides utilities for creating and managing
    error context information across the application.
    """
    
    @staticmethod
    def create_context(
        error: Exception,
        include_stack_trace: bool = True,
        **context_data: Any
    ) -> ErrorContext:
        """
        Create error context from exception.
        
        Args:
            error: The exception to create context from
            include_stack_trace: Whether to include stack trace
            **context_data: Additional context data
            
        Returns:
            ErrorContext: Created error context
        """
        import traceback
        
        context = ErrorContext(
            error_type=error.__class__.__name__,
            error_message=str(error),
            context_data=context_data
        )
        
        if include_stack_trace:
            context.stack_trace = traceback.format_exception(
                type(error),
                error,
                error.__traceback__
            )
        
        return context
    
    @staticmethod
    def format_context(context: ErrorContext) -> str:
        """
        Format error context as string.
        
        Args:
            context: Error context to format
            
        Returns:
            str: Formatted error context
        """
        parts = [
            f"Error: {context.error_type}",
            f"Message: {context.error_message}",
            f"Timestamp: {context.timestamp.isoformat()}"
        ]
        
        if context.context_data:
            context_str = ", ".join(
                f"{k}={v}" for k, v in context.context_data.items()
            )
            parts.append(f"Context: {context_str}")
        
        if context.recovery_attempted:
            recovery_status = "successful" if context.recovery_successful else "failed"
            parts.append(
                f"Recovery: {recovery_status} "
                f"(Strategy: {context.recovery_strategy or 'unknown'})"
            )
        
        if context.stack_trace:
            parts.append("Stack Trace:")
            parts.extend(context.stack_trace)
        
        return "\n".join(parts)
    
    @staticmethod
    def merge_contexts(*contexts: ErrorContext) -> ErrorContext:
        """
        Merge multiple error contexts.
        
        Args:
            *contexts: Error contexts to merge
            
        Returns:
            ErrorContext: Merged error context
        """
        if not contexts:
            return ErrorContext()
        
        # Use the first context as base
        merged = ErrorContext(
            timestamp=contexts[0].timestamp,
            error_type=contexts[0].error_type,
            error_message=contexts[0].error_message,
            stack_trace=contexts[0].stack_trace,
            context_data=contexts[0].context_data.copy(),
            recovery_attempted=contexts[0].recovery_attempted,
            recovery_successful=contexts[0].recovery_successful,
            recovery_strategy=contexts[0].recovery_strategy
        )
        
        # Merge additional contexts
        for context in contexts[1:]:
            merged.context_data.update(context.context_data)
            
            if context.recovery_attempted:
                merged.recovery_attempted = True
                merged.recovery_successful = context.recovery_successful
                merged.recovery_strategy = context.recovery_strategy
        
        return merged 