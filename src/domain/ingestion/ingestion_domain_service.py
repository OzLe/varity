"""
Domain service for ingestion operations.

This module contains pure business logic for ingestion operations,
separated from infrastructure concerns.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from ...core.entities import (
    IngestionProgress,
    IngestionResult,
    IngestionConfig,
    IngestionState,
    IngestionDecision,
    ValidationResult
)
from .validation_domain_service import ValidationDomainService
from .state_management_service import StateManagementService


class IngestionDomainService:
    """
    Domain service for ingestion operations.
    
    This service contains pure business logic for ingestion, with no
    dependencies on external systems or infrastructure.
    """
    
    def __init__(self):
        """Initialize the ingestion domain service."""
        self.validation_service = ValidationDomainService()
        self.state_service = StateManagementService()
    
    def calculate_progress(
        self,
        current_step: str,
        step_number: int,
        total_steps: int,
        items_processed: int,
        total_items: int,
        step_started_at: Optional[datetime] = None,
        average_step_duration: Optional[float] = None
    ) -> IngestionProgress:
        """
        Calculate ingestion progress.
        
        Args:
            current_step: Name of current step
            step_number: Current step number
            total_steps: Total number of steps
            items_processed: Number of items processed in current step
            total_items: Total items in current step
            step_started_at: When current step started
            average_step_duration: Average duration of previous steps
            
        Returns:
            IngestionProgress: Progress information
        """
        return IngestionProgress(
            current_step=current_step,
            step_number=step_number,
            total_steps=total_steps,
            items_processed=items_processed,
            total_items=total_items,
            step_started_at=step_started_at,
            average_step_duration=average_step_duration
        )
    
    def create_ingestion_result(
        self,
        success: bool,
        steps_completed: int,
        total_steps: int,
        errors: List[str],
        warnings: List[str],
        metrics: Dict[str, Any],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        final_state: Optional[IngestionState] = None,
        last_completed_step: str = ""
    ) -> IngestionResult:
        """
        Create ingestion result.
        
        Args:
            success: Whether ingestion was successful
            steps_completed: Number of steps completed
            total_steps: Total number of steps
            errors: List of errors encountered
            warnings: List of warnings encountered
            metrics: Dictionary of metrics
            start_time: When ingestion started
            end_time: When ingestion ended
            final_state: Final ingestion state
            last_completed_step: Last completed step name
            
        Returns:
            IngestionResult: Result information
        """
        return IngestionResult(
            success=success,
            steps_completed=steps_completed,
            total_steps=total_steps,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
            final_state=final_state,
            last_completed_step=last_completed_step
        )
    
    def validate_ingestion_prerequisites(
        self,
        config: IngestionConfig,
        required_files: List[str]
    ) -> ValidationResult:
        """
        Validate all ingestion prerequisites.
        
        Args:
            config: Ingestion configuration
            required_files: List of required data files
            
        Returns:
            ValidationResult: Validation status and details
        """
        # Validate configuration
        config_result = self.validation_service.validate_config(config)
        if not config_result.is_valid:
            return config_result
        
        # Validate data files
        data_result = self.validation_service.validate_data_files(
            config.data_dir,
            required_files
        )
        if not data_result.is_valid:
            return data_result
        
        # Combine results
        combined_result = ValidationResult(is_valid=True)
        combined_result.checks_performed.extend(config_result.checks_performed)
        combined_result.checks_performed.extend(data_result.checks_performed)
        combined_result.errors.extend(config_result.errors)
        combined_result.errors.extend(data_result.errors)
        combined_result.warnings.extend(config_result.warnings)
        combined_result.warnings.extend(data_result.warnings)
        combined_result.details.update(config_result.details)
        combined_result.details.update(data_result.details)
        
        return combined_result
    
    def determine_ingestion_state(
        self,
        status_data: Dict[str, Any],
        config: IngestionConfig
    ) -> IngestionState:
        """
        Determine current ingestion state.
        
        Args:
            status_data: Status data from storage
            config: Ingestion configuration
            
        Returns:
            IngestionState: Current ingestion state
        """
        return self.state_service.determine_ingestion_state(
            status_data,
            config.staleness_threshold_seconds
        )
    
    def make_ingestion_decision(
        self,
        current_state: IngestionState,
        existing_classes: List[str],
        config: IngestionConfig,
        timestamp: Optional[str] = None,
        is_stale: bool = False
    ) -> IngestionDecision:
        """
        Make decision about whether to run ingestion.
        
        Args:
            current_state: Current ingestion state
            existing_classes: List of existing classes
            config: Ingestion configuration
            timestamp: Optional timestamp of last state change
            is_stale: Whether current state is stale
            
        Returns:
            IngestionDecision: Decision with reasoning
        """
        return self.state_service.make_ingestion_decision(
            current_state=current_state,
            existing_classes=existing_classes,
            force_reingest=config.force_reingest,
            is_interactive=config.is_interactive_mode,
            timestamp=timestamp,
            is_stale=is_stale
        ) 