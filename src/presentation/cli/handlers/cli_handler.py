"""
CLI handler for managing command execution.

This module provides a base handler for CLI commands,
with support for command execution and error handling.
"""

from typing import Any, Callable, Dict, Optional, Type
from abc import ABC, abstractmethod
import sys
import traceback
from dataclasses import dataclass

from ...cli.formatters.output_formatter import OutputFormatter


@dataclass
class CommandResult:
    """Result of a command execution."""
    
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[Exception] = None


class CommandHandler(ABC):
    """
    Base class for command handlers.
    
    This class provides a base implementation for command handlers,
    with support for command execution and error handling.
    """
    
    def __init__(self, formatter: OutputFormatter):
        """
        Initialize the handler.
        
        Args:
            formatter: Output formatter
        """
        self.formatter = formatter
    
    @abstractmethod
    async def execute(self, **kwargs) -> CommandResult:
        """
        Execute the command.
        
        Args:
            **kwargs: Command arguments
            
        Returns:
            CommandResult: Command execution result
        """
        pass
    
    def handle_error(
        self,
        error: Exception,
        message: str = "An error occurred"
    ) -> CommandResult:
        """
        Handle command execution error.
        
        Args:
            error: Exception that occurred
            message: Error message
            
        Returns:
            CommandResult: Error result
        """
        error_details = str(error)
        if isinstance(error, Exception):
            error_details = traceback.format_exc()
        
        self.formatter.print(
            self.formatter.format_error(message, error_details)
        )
        
        return CommandResult(
            success=False,
            message=message,
            error=error
        )
    
    def handle_success(
        self,
        message: str,
        data: Optional[Any] = None,
        details: Optional[str] = None
    ) -> CommandResult:
        """
        Handle command execution success.
        
        Args:
            message: Success message
            data: Optional result data
            details: Optional success details
            
        Returns:
            CommandResult: Success result
        """
        self.formatter.print(
            self.formatter.format_success(message, details)
        )
        
        return CommandResult(
            success=True,
            message=message,
            data=data
        )


class CommandRegistry:
    """
    Registry for command handlers.
    
    This class manages command handlers and provides
    a way to execute commands by name.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._handlers: Dict[str, Type[CommandHandler]] = {}
    
    def register(
        self,
        name: str,
        handler: Type[CommandHandler]
    ) -> None:
        """
        Register a command handler.
        
        Args:
            name: Command name
            handler: Command handler class
        """
        self._handlers[name] = handler
    
    def get_handler(
        self,
        name: str
    ) -> Optional[Type[CommandHandler]]:
        """
        Get a command handler by name.
        
        Args:
            name: Command name
            
        Returns:
            Optional[Type[CommandHandler]]: Command handler class
        """
        return self._handlers.get(name)
    
    def list_commands(self) -> Dict[str, Type[CommandHandler]]:
        """
        List all registered commands.
        
        Returns:
            Dict[str, Type[CommandHandler]]: Command handlers
        """
        return self._handlers.copy()


class CLIApplication:
    """
    CLI application.
    
    This class manages the CLI application lifecycle,
    including command registration and execution.
    """
    
    def __init__(
        self,
        formatter: OutputFormatter,
        registry: Optional[CommandRegistry] = None
    ):
        """
        Initialize the application.
        
        Args:
            formatter: Output formatter
            registry: Optional command registry
        """
        self.formatter = formatter
        self.registry = registry or CommandRegistry()
    
    def register_command(
        self,
        name: str,
        handler: Type[CommandHandler]
    ) -> None:
        """
        Register a command.
        
        Args:
            name: Command name
            handler: Command handler class
        """
        self.registry.register(name, handler)
    
    async def execute_command(
        self,
        name: str,
        **kwargs
    ) -> CommandResult:
        """
        Execute a command.
        
        Args:
            name: Command name
            **kwargs: Command arguments
            
        Returns:
            CommandResult: Command execution result
        """
        handler_class = self.registry.get_handler(name)
        if not handler_class:
            return CommandResult(
                success=False,
                message=f"Unknown command: {name}"
            )
        
        handler = handler_class(self.formatter)
        try:
            return await handler.execute(**kwargs)
        except Exception as e:
            return handler.handle_error(e)
    
    def print_help(self) -> None:
        """Print help information."""
        commands = self.registry.list_commands()
        if not commands:
            self.formatter.print("No commands available")
            return
        
        help_data = [
            {
                "Command": name,
                "Description": handler.__doc__ or "No description"
            }
            for name, handler in commands.items()
        ]
        
        self.formatter.print(
            self.formatter.format_table(
                help_data,
                title="Available Commands"
            )
        ) 