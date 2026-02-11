"""
Configuration manager for centralized configuration handling.

This module provides a manager for loading and managing application
configurations, with support for different environments.
"""

from typing import Dict, Any, Optional
import os
import yaml
from pathlib import Path

from .config_validator import ConfigValidator
from .environment_config import EnvironmentConfig


class ConfigManager:
    """
    Manager for application configurations.
    
    This class handles loading and managing configurations,
    with support for different environments and validation.
    """
    
    def __init__(
        self,
        config_dir: str = "config",
        environment: Optional[str] = None
    ):
        """
        Initialize the manager.
        
        Args:
            config_dir: Configuration directory path
            environment: Optional environment name
        """
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("APP_ENV", "development")
        self.validator = ConfigValidator()
        self._config: Optional[Dict[str, Any]] = None
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from files.
        
        Returns:
            Dict[str, Any]: Loaded configuration
            
        Raises:
            FileNotFoundError: If configuration files are not found
            ValueError: If configuration is invalid
        """
        if self._config is not None:
            return self._config
        
        # Load base configuration
        base_config = self._load_yaml("base.yaml")
        
        # Load environment-specific configuration
        env_config = self._load_yaml(f"{self.environment}.yaml")
        
        # Merge configurations
        config = self._merge_configs(base_config, env_config)
        
        # Validate configuration
        self.validator.validate_config(config)
        
        # Create environment config
        self._config = EnvironmentConfig(config)
        
        return self._config
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Dict[str, Any]: Current configuration
        """
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration.
        
        Returns:
            Dict[str, Any]: Database configuration
        """
        config = self.get_config()
        return config.get("database", {})
    
    def get_ingestion_config(self) -> Dict[str, Any]:
        """
        Get ingestion configuration.
        
        Returns:
            Dict[str, Any]: Ingestion configuration
        """
        config = self.get_config()
        return config.get("ingestion", {})
    
    def get_search_config(self) -> Dict[str, Any]:
        """
        Get search configuration.
        
        Returns:
            Dict[str, Any]: Search configuration
        """
        config = self.get_config()
        return config.get("search", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Dict[str, Any]: Logging configuration
        """
        config = self.get_config()
        return config.get("logging", {})
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load YAML configuration file.
        
        Args:
            filename: Configuration file name
            
        Returns:
            Dict[str, Any]: Loaded configuration
            
        Raises:
            FileNotFoundError: If file is not found
        """
        file_path = self.config_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    
    def _merge_configs(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two configurations.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Dict[str, Any]: Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if (
                key in result and
                isinstance(result[key], dict) and
                isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result 