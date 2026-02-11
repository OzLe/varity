"""
Error recovery strategies.

This module provides standardized error recovery strategies
for handling different types of errors across the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Generic
from functools import wraps
import time

from .error_context import ErrorContext, ErrorContextManager

T = TypeVar('T')


class RecoveryStrategy(ABC, Generic[T]):
    """
    Base class for error recovery strategies.
    
    This abstract class defines the interface for error recovery
    strategies and provides common functionality.
    """
    
    def __init__(self, max_attempts: int = 3, delay: float = 1.0):
        """
        Initialize recovery strategy.
        
        Args:
            max_attempts: Maximum number of recovery attempts
            delay: Delay between attempts in seconds
        """
        self.max_attempts = max_attempts
        self.delay = delay
    
    @abstractmethod
    def can_handle(self, error: Exception) -> bool:
        """
        Check if strategy can handle the error.
        
        Args:
            error: The error to check
            
        Returns:
            bool: Whether strategy can handle the error
        """
        pass
    
    @abstractmethod
    async def recover(self, error: Exception, context: ErrorContext) -> T:
        """
        Attempt to recover from error.
        
        Args:
            error: The error to recover from
            context: Error context
            
        Returns:
            T: Recovery result
            
        Raises:
            Exception: If recovery fails
        """
        pass


class RetryStrategy(RecoveryStrategy[T]):
    """
    Retry strategy for transient errors.
    
    This strategy retries operations that fail due to
    transient errors like network issues.
    """
    
    def __init__(
        self,
        operation: Callable[..., T],
        error_types: tuple[Type[Exception], ...],
        max_attempts: int = 3,
        delay: float = 1.0
    ):
        """
        Initialize retry strategy.
        
        Args:
            operation: Operation to retry
            error_types: Types of errors to retry on
            max_attempts: Maximum number of retry attempts
            delay: Delay between attempts in seconds
        """
        super().__init__(max_attempts, delay)
        self.operation = operation
        self.error_types = error_types
    
    def can_handle(self, error: Exception) -> bool:
        """Check if error is retryable."""
        return isinstance(error, self.error_types)
    
    async def recover(self, error: Exception, context: ErrorContext) -> T:
        """Attempt to recover by retrying operation."""
        for attempt in range(self.max_attempts):
            try:
                # Update context
                context.add_context(
                    retry_attempt=attempt + 1,
                    max_attempts=self.max_attempts
                )
                
                # Attempt operation
                result = await self.operation()
                
                # Update recovery status
                context.set_recovery_status(
                    attempted=True,
                    successful=True,
                    strategy="retry"
                )
                
                return result
            
            except Exception as e:
                if attempt == self.max_attempts - 1:
                    # Update recovery status
                    context.set_recovery_status(
                        attempted=True,
                        successful=False,
                        strategy="retry"
                    )
                    raise
                
                # Wait before retry (async-safe)
                import asyncio
                await asyncio.sleep(self.delay)


class FallbackStrategy(RecoveryStrategy[T]):
    """
    Fallback strategy for handling errors.
    
    This strategy provides a fallback operation when
    the primary operation fails.
    """
    
    def __init__(
        self,
        fallback_operation: Callable[..., T],
        error_types: tuple[Type[Exception], ...]
    ):
        """
        Initialize fallback strategy.
        
        Args:
            fallback_operation: Fallback operation
            error_types: Types of errors to handle
        """
        super().__init__(max_attempts=1)
        self.fallback_operation = fallback_operation
        self.error_types = error_types
    
    def can_handle(self, error: Exception) -> bool:
        """Check if error can be handled by fallback."""
        return isinstance(error, self.error_types)
    
    async def recover(self, error: Exception, context: ErrorContext) -> T:
        """Attempt to recover using fallback operation."""
        try:
            # Update context
            context.add_context(fallback_used=True)
            
            # Attempt fallback
            result = await self.fallback_operation()
            
            # Update recovery status
            context.set_recovery_status(
                attempted=True,
                successful=True,
                strategy="fallback"
            )
            
            return result
        
        except Exception as e:
            # Update recovery status
            context.set_recovery_status(
                attempted=True,
                successful=False,
                strategy="fallback"
            )
            raise


class CircuitBreakerStrategy(RecoveryStrategy[T]):
    """
    Circuit breaker strategy for handling errors.
    
    This strategy prevents repeated attempts to failing
    operations by breaking the circuit after a threshold.
    """
    
    def __init__(
        self,
        operation: Callable[..., T],
        error_types: tuple[Type[Exception], ...],
        failure_threshold: int = 5,
        reset_timeout: float = 60.0
    ):
        """
        Initialize circuit breaker strategy.
        
        Args:
            operation: Operation to protect
            error_types: Types of errors to track
            failure_threshold: Number of failures before breaking
            reset_timeout: Time in seconds before resetting
        """
        super().__init__(max_attempts=1)
        self.operation = operation
        self.error_types = error_types
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.circuit_open = False
    
    def can_handle(self, error: Exception) -> bool:
        """Check if error should be tracked."""
        return isinstance(error, self.error_types)
    
    async def recover(self, error: Exception, context: ErrorContext) -> T:
        """Attempt to recover using circuit breaker."""
        current_time = time.time()
        
        # Check if circuit should be reset
        if (
            self.circuit_open and
            current_time - self.last_failure_time > self.reset_timeout
        ):
            self.circuit_open = False
            self.failures = 0
        
        # Check if circuit is open
        if self.circuit_open:
            context.add_context(
                circuit_open=True,
                failures=self.failures,
                last_failure=self.last_failure_time
            )
            context.set_recovery_status(
                attempted=False,
                successful=False,
                strategy="circuit_breaker"
            )
            raise error
        
        try:
            # Attempt operation
            result = await self.operation()
            
            # Reset failures on success
            self.failures = 0
            
            # Update recovery status
            context.set_recovery_status(
                attempted=True,
                successful=True,
                strategy="circuit_breaker"
            )
            
            return result
        
        except Exception as e:
            # Update failure count
            self.failures += 1
            self.last_failure_time = current_time
            
            # Check if circuit should be opened
            if self.failures >= self.failure_threshold:
                self.circuit_open = True
            
            # Update context
            context.add_context(
                failures=self.failures,
                circuit_open=self.circuit_open,
                last_failure=self.last_failure_time
            )
            
            # Update recovery status
            context.set_recovery_status(
                attempted=True,
                successful=False,
                strategy="circuit_breaker"
            )
            
            raise


def with_recovery(
    *strategies: RecoveryStrategy,
    context_data: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator for adding recovery strategies to functions.
    
    Args:
        *strategies: Recovery strategies to apply
        context_data: Optional context data
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:
                # Create error context
                context = ErrorContextManager.create_context(
                    e,
                    **(context_data or {})
                )
                
                # Try each strategy
                for strategy in strategies:
                    if strategy.can_handle(e):
                        try:
                            return await strategy.recover(e, context)
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
                
                # If no strategy succeeded, raise original error
                raise e
        
        return wrapper
    
    return decorator 