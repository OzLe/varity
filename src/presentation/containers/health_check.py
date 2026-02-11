"""
Health check utilities for containers.

This module provides health check functionality for containers,
including database connectivity, service status, and resource usage.
"""

from typing import Dict, Any, List, Optional
import time
import psutil
import asyncio
from dataclasses import dataclass
from datetime import datetime

from ...infrastructure.database.factory import DatabaseFactory
from ...infrastructure.config.config_manager import ConfigManager


@dataclass
class HealthStatus:
    """Health check status."""
    
    status: str
    timestamp: datetime
    details: Dict[str, Any]
    errors: List[str]


class HealthChecker:
    """
    Health checker for containers.
    
    This class provides methods for checking the health of
    various system components.
    """
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        database_factory: Optional[DatabaseFactory] = None
    ):
        """
        Initialize the health checker.
        
        Args:
            config_manager: Optional config manager
            database_factory: Optional database factory
        """
        self.config_manager = config_manager or ConfigManager()
        self.database_factory = database_factory or DatabaseFactory()
    
    async def check_health(self) -> HealthStatus:
        """
        Perform a complete health check.
        
        Returns:
            HealthStatus: Health check status
        """
        status = "healthy"
        details = {}
        errors = []
        
        # Check database
        try:
            db_status = await self._check_database()
            details["database"] = db_status
            if not db_status["healthy"]:
                status = "unhealthy"
                errors.append("Database check failed")
        except Exception as e:
            status = "unhealthy"
            errors.append(f"Database check error: {str(e)}")
        
        # Check system resources
        try:
            resource_status = self._check_resources()
            details["resources"] = resource_status
            if not resource_status["healthy"]:
                status = "unhealthy"
                errors.append("Resource check failed")
        except Exception as e:
            status = "unhealthy"
            errors.append(f"Resource check error: {str(e)}")
        
        # Check configuration
        try:
            config_status = self._check_configuration()
            details["configuration"] = config_status
            if not config_status["healthy"]:
                status = "unhealthy"
                errors.append("Configuration check failed")
        except Exception as e:
            status = "unhealthy"
            errors.append(f"Configuration check error: {str(e)}")
        
        return HealthStatus(
            status=status,
            timestamp=datetime.utcnow(),
            details=details,
            errors=errors
        )
    
    async def _check_database(self) -> Dict[str, Any]:
        """
        Check database health.
        
        Returns:
            Dict[str, Any]: Database health status
        """
        start_time = time.time()
        try:
            # Get database client
            db = self.database_factory.create_database()
            
            # Check connection
            is_connected = await db.is_connected()
            
            # Get database info
            info = await db.get_info()
            
            return {
                "healthy": is_connected,
                "connection_time": time.time() - start_time,
                "info": info
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "connection_time": time.time() - start_time
            }
    
    def _check_resources(self) -> Dict[str, Any]:
        """
        Check system resources.
        
        Returns:
            Dict[str, Any]: Resource health status
        """
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            
            # Define thresholds
            cpu_threshold = 90
            memory_threshold = 90
            disk_threshold = 90
            
            # Check if any resource is above threshold
            is_healthy = (
                cpu_percent < cpu_threshold and
                memory.percent < memory_threshold and
                disk.percent < disk_threshold
            )
            
            return {
                "healthy": is_healthy,
                "cpu": {
                    "usage": cpu_percent,
                    "threshold": cpu_threshold
                },
                "memory": {
                    "usage": memory.percent,
                    "available": memory.available,
                    "threshold": memory_threshold
                },
                "disk": {
                    "usage": disk.percent,
                    "free": disk.free,
                    "threshold": disk_threshold
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_configuration(self) -> Dict[str, Any]:
        """
        Check configuration health.
        
        Returns:
            Dict[str, Any]: Configuration health status
        """
        try:
            # Load configuration
            config = self.config_manager.load_config()
            
            # Validate configuration
            is_valid = self.config_manager.validate_config(config)
            
            return {
                "healthy": is_valid,
                "config": {
                    "environment": config.get("environment", "unknown"),
                    "database": bool(config.get("database")),
                    "ingestion": bool(config.get("ingestion")),
                    "search": bool(config.get("search"))
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }


class HealthMonitor:
    """
    Health monitor for containers.
    
    This class provides continuous health monitoring
    and status reporting.
    """
    
    def __init__(
        self,
        health_checker: HealthChecker,
        check_interval: int = 60
    ):
        """
        Initialize the health monitor.
        
        Args:
            health_checker: Health checker instance
            check_interval: Interval between checks in seconds
        """
        self.health_checker = health_checker
        self.check_interval = check_interval
        self._last_status: Optional[HealthStatus] = None
        self._monitoring = False
    
    async def start_monitoring(self) -> None:
        """Start health monitoring."""
        self._monitoring = True
        while self._monitoring:
            try:
                self._last_status = await self.health_checker.check_health()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"Health check failed: {str(e)}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self._monitoring = False
    
    def get_last_status(self) -> Optional[HealthStatus]:
        """
        Get the last health check status.
        
        Returns:
            Optional[HealthStatus]: Last health check status
        """
        return self._last_status 