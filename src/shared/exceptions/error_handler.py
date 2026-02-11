"""
Error handler for centralized error handling.

This module provides centralized error handling and management
across the application.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar
from functools import wraps

from .error_context import ErrorContext, ErrorContextManager
from .recovery_strategies import RecoveryStrategy

T = TypeVar('T')


class ErrorHandler:
    """
    Centralized error handler.
    
    This class provides centralized error handling and management
    across the application.
    """
    
    def __init__(self):
        """Initialize error handler."""
        self._handlers: Dict[Type[Exception], Callable] = {}
        self._recovery_strategies: Dict[Type[Exception], list[RecoveryStrategy]] = {}
        self._error_callbacks: list[Callable[[Exception, ErrorContext], None]] = []
    
    def register_handler(
        self,
        error_type: Type[Exception],
        handler: Callable[[Exception, ErrorContext], Any]
    ) -> None:
        """
        Register error handler.
        
        Args:
            error_type: Type of error to handle
            handler: Handler function
        """
        self._handlers[error_type] = handler
    
    def register_recovery_strategy(
        self,
        error_type: Type[Exception],
        strategy: RecoveryStrategy
    ) -> None:
        """
        Register recovery strategy.
        
        Args:
            error_type: Type of error to handle
            strategy: Recovery strategy
        """
        if error_type not in self._recovery_strategies:
            self._recovery_strategies[error_type] = []
        self._recovery_strategies[error_type].append(strategy)
    
    def register_error_callback(
        self,
        callback: Callable[[Exception, ErrorContext], None]
    ) -> None:
        """
        Register error callback.
        
        Args:
            callback: Callback function
        """
        self._error_callbacks.append(callback)
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        **context_data: Any
    ) -> Any:
        """
        Handle error.
        
        Args:
            error: Error to handle
            context: Optional error context
            **context_data: Additional context data
            
        Returns:
            Any: Handler result if successful
            
        Raises:
            Exception: If no handler succeeds
        """
        # Create context if not provided
        if context is None:
            context = ErrorContextManager.create_context(
                error,
                **context_data
            )
        
        # Try recovery strategies
        error_type = type(error)
        if error_type in self._recovery_strategies:
            for strategy in self._recovery_strategies[error_type]:
                if strategy.can_handle(error):
                    try:
                        return await strategy.recover(error, context)
                    except Exception as recovery_error:
                        # Update context with recovery error
                        recovery_context = ErrorContextManager.create_context(
                            recovery_error,
                            recovery_attempted=True,
                            recovery_successful=False,
                            recovery_strategy=strategy.__class__.__name__
                        )
                        context = ErrorContextManager.merge_contexts(
                            context,
                            recovery_context
                        )
        
        # Try error handlers
        for error_type, handler in self._handlers.items():
            if isinstance(error, error_type):
                try:
                    return await handler(error, context)
                except Exception as handler_error:
                    # Update context with handler error
                    handler_context = ErrorContextManager.create_context(
                        handler_error,
                        handler_error=True
                    )
                    context = ErrorContextManager.merge_contexts(
                        context,
                        handler_context
                    )
        
        # Call error callbacks
        for callback in self._error_callbacks:
            try:
                await callback(error, context)
            except Exception as callback_error:
                # Update context with callback error
                callback_context = ErrorContextManager.create_context(
                    callback_error,
                    callback_error=True
                )
                context = ErrorContextManager.merge_contexts(
                    context,
                    callback_context
                )
        
        # If no handler succeeded, raise original error
        raise error
    
    def handle_errors(
        self,
        *error_types: Type[Exception],
        **context_data: Any
    ) -> Callable:
        """
        Decorator for handling errors.
        
        Args:
            *error_types: Types of errors to handle
            **context_data: Additional context data
            
        Returns:
            Callable: Decorated function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                try:
                    return await func(*args, **kwargs)
                
                except Exception as e:
                    # Check if error type should be handled
                    if error_types and not any(
                        isinstance(e, error_type)
                        for error_type in error_types
                    ):
                        raise
                    
                    # Handle error
                    return await self.handle_error(
                        e,
                        **context_data
                    )
            
            return wrapper
        
        return decorator


# Create global error handler
error_handler = ErrorHandler()


def handle_errors(
    *error_types: Type[Exception],
    **context_data: Any
) -> Callable:
    """
    Decorator for handling errors using global error handler.
    
    Args:
        *error_types: Types of errors to handle
        **context_data: Additional context data
        
    Returns:
        Callable: Decorated function
    """
    return error_handler.handle_errors(*error_types, **context_data) 