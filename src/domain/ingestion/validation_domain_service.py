"""
Domain service for ingestion validation.

This service provides validation logic for configuration and data files
in the ingestion pipeline.
"""

import os
from typing import Optional, Dict, Any, List

from ...core.entities import ValidationResult, IngestionConfig


class ValidationDomainService:
    """Service for validating ingestion prerequisites."""

    def validate_config(self, config: IngestionConfig) -> ValidationResult:
        """
        Validate the ingestion configuration.

        Args:
            config: Ingestion configuration to validate

        Returns:
            ValidationResult: Validation status and details
        """
        return config.validate()

    def validate_data_files(
        self, data_dir: str, required_files: List[str]
    ) -> ValidationResult:
        """
        Validate that required data files exist and are readable.

        Args:
            data_dir: Directory containing data files
            required_files: List of required file names

        Returns:
            ValidationResult: Validation status and details
        """
        result = ValidationResult(is_valid=True)
        result.checks_performed.append("data_files_validation")

        if not data_dir:
            result.add_error("data_dir is not configured", "data_files")
            return result

        if not os.path.isdir(data_dir):
            result.add_error(
                f"Data directory does not exist: {data_dir}", "data_files"
            )
            return result

        for filename in required_files:
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath):
                result.add_warning(
                    f"Data file not found: {filename}", "data_files"
                )
            elif not os.access(filepath, os.R_OK):
                result.add_error(
                    f"Data file not readable: {filename}", "data_files"
                )

        if result.is_valid:
            result.add_success("Data files validation passed", "data_files")

        return result
