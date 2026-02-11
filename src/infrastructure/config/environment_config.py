"""
Environment configuration for environment-specific settings.

This module provides configuration settings specific to different
environments (development, staging, production).
"""

from typing import Dict, Any, Optional
import os


class EnvironmentConfig:
    """
    Environment-specific configuration.
    
    This class provides configuration settings specific to different
    environments, with support for environment variables.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the configuration.
        
        Args:
            config: Base configuration
        """
        self.config = config
        self._apply_environment_overrides()
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Database configuration
        if "database" in self.config:
            db_config = self.config["database"]
            
            # Override URL
            if "WEAVIATE_URL" in os.environ:
                db_config["url"] = os.environ["WEAVIATE_URL"]
            
            # Override API key
            if "WEAVIATE_API_KEY" in os.environ:
                db_config["api_key"] = os.environ["WEAVIATE_API_KEY"]
        
        # Logging configuration
        if "logging" in self.config:
            log_config = self.config["logging"]
            
            # Override level
            if "LOG_LEVEL" in os.environ:
                log_config["level"] = os.environ["LOG_LEVEL"]
            
            # Override file path
            if "LOG_FILE" in os.environ:
                log_config["file"] = os.environ["LOG_FILE"]
    
    def get_database_url(self) -> str:
        """
        Get database URL.
        
        Returns:
            str: Database URL
        """
        return self.config["database"]["url"]
    
    def get_database_api_key(self) -> Optional[str]:
        """
        Get database API key.
        
        Returns:
            Optional[str]: Database API key
        """
        return self.config["database"].get("api_key")
    
    def get_database_timeout(self) -> float:
        """
        Get database timeout.
        
        Returns:
            float: Database timeout in seconds
        """
        return self.config["database"].get("timeout_seconds", 60.0)
    
    def get_ingestion_batch_size(self) -> int:
        """
        Get ingestion batch size.
        
        Returns:
            int: Batch size
        """
        return self.config["ingestion"].get("batch_size", 100)
    
    def get_ingestion_retry_attempts(self) -> int:
        """
        Get ingestion retry attempts.
        
        Returns:
            int: Number of retry attempts
        """
        return self.config["ingestion"].get("retry_attempts", 3)
    
    def get_ingestion_timeout(self) -> float:
        """
        Get ingestion timeout.
        
        Returns:
            float: Timeout in seconds
        """
        return self.config["ingestion"].get("timeout_seconds", 300.0)
    
    def get_search_default_limit(self) -> int:
        """
        Get search default limit.
        
        Returns:
            int: Default result limit
        """
        return self.config["search"].get("default_limit", 10)
    
    def get_search_max_limit(self) -> int:
        """
        Get search maximum limit.
        
        Returns:
            int: Maximum result limit
        """
        return self.config["search"].get("max_limit", 100)
    
    def get_search_timeout(self) -> float:
        """
        Get search timeout.
        
        Returns:
            float: Timeout in seconds
        """
        return self.config["search"].get("timeout_seconds", 30.0)
    
    def get_log_level(self) -> str:
        """
        Get logging level.
        
        Returns:
            str: Logging level
        """
        return self.config["logging"].get("level", "INFO")
    
    def get_log_format(self) -> str:
        """
        Get logging format.
        
        Returns:
            str: Logging format
        """
        return self.config["logging"].get(
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    def get_log_file(self) -> Optional[str]:
        """
        Get logging file path.
        
        Returns:
            Optional[str]: Log file path
        """
        return self.config["logging"].get("file") 