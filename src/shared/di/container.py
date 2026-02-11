"""
Dependency injection container.

This module provides the dependency injection container that manages
service resolution and lifecycle.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, get_type_hints

from .lifetime_manager import LifetimeManager, scope_context
from .service_registry import ServiceLifetime, ServiceRegistration, ServiceRegistry

T = TypeVar('T')


class Container:
    """
    Dependency injection container.
    
    This class manages service registration, resolution, and lifecycle.
    It provides a fluent interface for configuring services and handles
    dependency resolution.
    """
    
    def __init__(self):
        """Initialize container."""
        self._registry = ServiceRegistry()
        self._lifetime_manager = LifetimeManager()
        self._current_scope: Optional[Any] = None
    
    def register(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        factory: Optional[Callable[..., T]] = None
    ) -> 'Container':
        """
        Register a service type with its implementation.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            lifetime: Service lifetime
            factory: Optional factory function for creating instances
            
        Returns:
            Container: Self for method chaining
        """
        self._registry.register(
            service_type=service_type,
            implementation=implementation,
            lifetime=lifetime,
            factory=factory
        )
        return self
    
    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        factory: Optional[Callable[..., T]] = None
    ) -> 'Container':
        """
        Register a singleton service.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            factory: Optional factory function for creating instances
            
        Returns:
            Container: Self for method chaining
        """
        self._registry.register_singleton(
            service_type=service_type,
            implementation=implementation,
            factory=factory
        )
        return self
    
    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        factory: Optional[Callable[..., T]] = None
    ) -> 'Container':
        """
        Register a scoped service.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            factory: Optional factory function for creating instances
            
        Returns:
            Container: Self for method chaining
        """
        self._registry.register_scoped(
            service_type=service_type,
            implementation=implementation,
            factory=factory
        )
        return self
    
    def register_transient(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        factory: Optional[Callable[..., T]] = None
    ) -> 'Container':
        """
        Register a transient service.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            factory: Optional factory function for creating instances
            
        Returns:
            Container: Self for method chaining
        """
        self._registry.register_transient(
            service_type=service_type,
            implementation=implementation,
            factory=factory
        )
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance.
        
        Args:
            service_type: Type of service to resolve
            
        Returns:
            T: Resolved service instance
            
        Raises:
            ValueError: If service type is not registered
        """
        registration = self._registry.get_registration(service_type)
        if not registration:
            raise ValueError(f"Service type {service_type} is not registered")
        
        factory = registration.factory or self._create_factory(registration)
        return self._lifetime_manager.get_instance(
            registration=registration,
            factory=factory,
            scope=self._current_scope
        )
    
    def create_scope(self) -> 'Container':
        """
        Create a new scope.
        
        Returns:
            Container: New container instance with scope
        """
        scoped_container = Container()
        scoped_container._registry = self._registry
        scoped_container._lifetime_manager = self._lifetime_manager
        scoped_container._current_scope = object()
        return scoped_container
    
    @scope_context
    def scope(self) -> 'Container':
        """
        Create a scoped context.
        
        Returns:
            Container: Container instance with scope
        """
        return self.create_scope()
    
    def _create_factory(
        self,
        registration: ServiceRegistration
    ) -> Callable[..., Any]:
        """
        Create factory function for service.
        
        Args:
            registration: Service registration
            
        Returns:
            Callable[..., Any]: Factory function
        """
        implementation = registration.implementation
        
        if callable(implementation) and not isinstance(implementation, type):
            return implementation
        
        if isinstance(implementation, type):
            return lambda: self._create_instance(implementation)
        
        raise ValueError(f"Invalid implementation type: {type(implementation)}")
    
    def _create_instance(self, implementation_type: Type) -> Any:
        """
        Create instance of implementation type.
        
        Args:
            implementation_type: Type to create instance of
            
        Returns:
            Any: Created instance
        """
        constructor = implementation_type.__init__
        signature = inspect.signature(constructor)
        type_hints = get_type_hints(constructor)
        
        # Skip 'self' parameter
        parameters = list(signature.parameters.keys())[1:]
        
        # Resolve dependencies
        dependencies = {}
        for param in parameters:
            param_type = type_hints.get(param)
            if param_type:
                dependencies[param] = self.resolve(param_type)
        
        # Create instance
        instance = implementation_type(**dependencies)
        return instance
    
    def dispose(self) -> None:
        """Dispose all tracked instances."""
        self._lifetime_manager.dispose_all()


# Global container instance
container = Container() 