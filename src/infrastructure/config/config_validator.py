"""
Configuration validator for validating configuration values.

This module provides a validator for ensuring configuration values
meet the required format and constraints.
"""

from typing import Dict, Any, List, Optional
import re


class ConfigValidator:
    """
    Validator for configuration values.
    
    This class validates configuration values to ensure they meet
    the required format and constraints.
    """
    
    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        self.errors = []
        
        # Validate database configuration
        if "database" in config:
            self._validate_database_config(config["database"])
        
        # Validate ingestion configuration
        if "ingestion" in config:
            self._validate_ingestion_config(config["ingestion"])
        
        # Validate search configuration
        if "search" in config:
            self._validate_search_config(config["search"])
        
        # Validate logging configuration
        if "logging" in config:
            self._validate_logging_config(config["logging"])
        
        # Raise error if validation failed
        if self.errors:
            raise ValueError("\n".join(self.errors))
    
    def _validate_database_config(self, config: Dict[str, Any]) -> None:
        """
        Validate database configuration.
        
        Args:
            config: Database configuration
        """
        # Validate required fields
        required_fields = ["url", "type"]
        for field in required_fields:
            if field not in config:
                self.errors.append(f"Missing required database field: {field}")
        
        # Validate URL format
        if "url" in config:
            url = config["url"]
            if not isinstance(url, str) or not url:
                self.errors.append("Database URL must be a non-empty string")
            elif not re.match(r"^https?://", url):
                self.errors.append("Database URL must start with http:// or https://")
        
        # Validate type
        if "type" in config:
            db_type = config["type"]
            if not isinstance(db_type, str) or db_type not in ["weaviate"]:
                self.errors.append("Database type must be 'weaviate'")
        
        # Validate optional fields
        if "api_key" in config:
            api_key = config["api_key"]
            if not isinstance(api_key, str) or not api_key:
                self.errors.append("Database API key must be a non-empty string")
        
        if "timeout_seconds" in config:
            timeout = config["timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                self.errors.append("Database timeout must be a positive number")
    
    def _validate_ingestion_config(self, config: Dict[str, Any]) -> None:
        """
        Validate ingestion configuration.
        
        Args:
            config: Ingestion configuration
        """
        # Validate batch size
        if "batch_size" in config:
            batch_size = config["batch_size"]
            if not isinstance(batch_size, int) or batch_size <= 0:
                self.errors.append("Ingestion batch size must be a positive integer")
        
        # Validate retry attempts
        if "retry_attempts" in config:
            retries = config["retry_attempts"]
            if not isinstance(retries, int) or retries < 0:
                self.errors.append("Ingestion retry attempts must be a non-negative integer")
        
        # Validate timeout
        if "timeout_seconds" in config:
            timeout = config["timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                self.errors.append("Ingestion timeout must be a positive number")
    
    def _validate_search_config(self, config: Dict[str, Any]) -> None:
        """
        Validate search configuration.
        
        Args:
            config: Search configuration
        """
        # Validate default limit
        if "default_limit" in config:
            limit = config["default_limit"]
            if not isinstance(limit, int) or limit <= 0:
                self.errors.append("Search default limit must be a positive integer")
        
        # Validate max limit
        if "max_limit" in config:
            max_limit = config["max_limit"]
            if not isinstance(max_limit, int) or max_limit <= 0:
                self.errors.append("Search max limit must be a positive integer")
        
        # Validate timeout
        if "timeout_seconds" in config:
            timeout = config["timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                self.errors.append("Search timeout must be a positive number")
    
    def _validate_logging_config(self, config: Dict[str, Any]) -> None:
        """
        Validate logging configuration.
        
        Args:
            config: Logging configuration
        """
        # Validate level
        if "level" in config:
            level = config["level"]
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if not isinstance(level, str) or level not in valid_levels:
                self.errors.append(
                    f"Logging level must be one of: {', '.join(valid_levels)}"
                )
        
        # Validate format
        if "format" in config:
            fmt = config["format"]
            if not isinstance(fmt, str) or not fmt:
                self.errors.append("Logging format must be a non-empty string")
        
        # Validate file path
        if "file" in config:
            file_path = config["file"]
            if not isinstance(file_path, str) or not file_path:
                self.errors.append("Logging file path must be a non-empty string") 