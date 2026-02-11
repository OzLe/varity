"""
Lifetime manager for dependency injection.

This module provides the lifetime manager that handles service
instance lifecycle and disposal.
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Type
from weakref import WeakKeyDictionary

from .service_registry import ServiceLifetime, ServiceRegistration


class LifetimeManager:
    """
    Manager for service instance lifecycle.
    
    This class manages the creation, caching, and disposal of
    service instances based on their lifetime.
    """
    
    def __init__(self):
        """Initialize lifetime manager."""
        self._singleton_instances: Dict[Type, Any] = {}
        self._scoped_instances: WeakKeyDictionary = WeakKeyDictionary()
        self._disposables: List[Any] = []
    
    def get_instance(
        self,
        registration: ServiceRegistration,
        factory: callable,
        scope: Optional[Any] = None
    ) -> Any:
        """
        Get or create service instance.
        
        Args:
            registration: Service registration
            factory: Factory function for creating instance
            scope: Optional scope for scoped services
            
        Returns:
            Any: Service instance
        """
        if registration.lifetime == ServiceLifetime.SINGLETON:
            return self._get_singleton_instance(registration, factory)
        
        if registration.lifetime == ServiceLifetime.SCOPED:
            return self._get_scoped_instance(registration, factory, scope)
        
        return self._create_transient_instance(registration, factory)
    
    def _get_singleton_instance(
        self,
        registration: ServiceRegistration,
        factory: callable
    ) -> Any:
        """
        Get or create singleton instance.
        
        Args:
            registration: Service registration
            factory: Factory function for creating instance
            
        Returns:
            Any: Singleton instance
        """
        if registration.service_type not in self._singleton_instances:
            instance = factory()
            self._singleton_instances[registration.service_type] = instance
            self._track_disposable(instance)
        
        return self._singleton_instances[registration.service_type]
    
    def _get_scoped_instance(
        self,
        registration: ServiceRegistration,
        factory: callable,
        scope: Optional[Any]
    ) -> Any:
        """
        Get or create scoped instance.
        
        Args:
            registration: Service registration
            factory: Factory function for creating instance
            scope: Scope for scoped service
            
        Returns:
            Any: Scoped instance
        """
        if scope is None:
            raise ValueError("Scope is required for scoped services")
        
        if scope not in self._scoped_instances:
            self._scoped_instances[scope] = {}
        
        scope_instances = self._scoped_instances[scope]
        
        if registration.service_type not in scope_instances:
            instance = factory()
            scope_instances[registration.service_type] = instance
            self._track_disposable(instance)
        
        return scope_instances[registration.service_type]
    
    def _create_transient_instance(
        self,
        registration: ServiceRegistration,
        factory: callable
    ) -> Any:
        """
        Create transient instance.
        
        Args:
            registration: Service registration
            factory: Factory function for creating instance
            
        Returns:
            Any: Transient instance
        """
        instance = factory()
        self._track_disposable(instance)
        return instance
    
    def _track_disposable(self, instance: Any) -> None:
        """
        Track disposable instance.
        
        Args:
            instance: Instance to track
        """
        if hasattr(instance, "dispose"):
            self._disposables.append(instance)
    
    def dispose_scope(self, scope: Any) -> None:
        """
        Dispose all instances in a scope.
        
        Args:
            scope: Scope to dispose
        """
        if scope in self._scoped_instances:
            for instance in self._scoped_instances[scope].values():
                if hasattr(instance, "dispose"):
                    instance.dispose()
            del self._scoped_instances[scope]
    
    def dispose_all(self) -> None:
        """Dispose all tracked instances."""
        for instance in self._disposables:
            if hasattr(instance, "dispose"):
                instance.dispose()
        
        self._singleton_instances.clear()
        self._scoped_instances.clear()
        self._disposables.clear()


@contextmanager
def scope_context(manager: LifetimeManager, scope: Any):
    """
    Context manager for scoped services.
    
    Args:
        manager: Lifetime manager
        scope: Scope for services
    """
    try:
        yield
    finally:
        manager.dispose_scope(scope) 