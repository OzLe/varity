"""
Service registry for dependency injection.

This module provides the service registry that manages service
registrations and their lifetimes.
"""

from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime options."""
    
    SINGLETON = "singleton"  # Single instance for entire application
    SCOPED = "scoped"       # Single instance per scope
    TRANSIENT = "transient" # New instance per request


class ServiceRegistration:
    """Registration information for a service."""
    
    def __init__(
        self,
        service_type: Type,
        implementation: Union[Type, Callable[..., Any]],
        lifetime: ServiceLifetime,
        factory: Optional[Callable[..., Any]] = None
    ):
        """
        Initialize service registration.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            lifetime: Service lifetime
            factory: Optional factory function for creating instances
        """
        self.service_type = service_type
        self.implementation = implementation
        self.lifetime = lifetime
        self.factory = factory
        self.instance: Optional[Any] = None


class ServiceRegistry:
    """
    Registry for managing service registrations.
    
    This class maintains a registry of service types and their
    implementations, along with lifetime management.
    """
    
    def __init__(self):
        """Initialize service registry."""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._scoped_instances: Dict[Type, Any] = {}
    
    def register(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        factory: Optional[Callable[..., T]] = None
    ) -> None:
        """
        Register a service type with its implementation.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            lifetime: Service lifetime
            factory: Optional factory function for creating instances
        """
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            implementation=implementation,
            lifetime=lifetime,
            factory=factory
        )
    
    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        factory: Optional[Callable[..., T]] = None
    ) -> None:
        """
        Register a singleton service.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            factory: Optional factory function for creating instances
        """
        self.register(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SINGLETON,
            factory=factory
        )
    
    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        factory: Optional[Callable[..., T]] = None
    ) -> None:
        """
        Register a scoped service.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            factory: Optional factory function for creating instances
        """
        self.register(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SCOPED,
            factory=factory
        )
    
    def register_transient(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        factory: Optional[Callable[..., T]] = None
    ) -> None:
        """
        Register a transient service.
        
        Args:
            service_type: Type of service being registered
            implementation: Implementation type or factory function
            factory: Optional factory function for creating instances
        """
        self.register(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.TRANSIENT,
            factory=factory
        )
    
    def get_registration(self, service_type: Type) -> Optional[ServiceRegistration]:
        """
        Get registration for a service type.
        
        Args:
            service_type: Type of service to get registration for
            
        Returns:
            Optional[ServiceRegistration]: Service registration if found
        """
        return self._registrations.get(service_type)
    
    def clear_scoped_instances(self) -> None:
        """Clear all scoped service instances."""
        self._scoped_instances.clear()
    
    def get_scoped_instance(self, service_type: Type) -> Optional[Any]:
        """
        Get scoped instance for a service type.
        
        Args:
            service_type: Type of service to get instance for
            
        Returns:
            Optional[Any]: Scoped instance if found
        """
        return self._scoped_instances.get(service_type)
    
    def set_scoped_instance(self, service_type: Type, instance: Any) -> None:
        """
        Set scoped instance for a service type.
        
        Args:
            service_type: Type of service to set instance for
            instance: Service instance
        """
        self._scoped_instances[service_type] = instance 