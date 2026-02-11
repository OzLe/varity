"""
Domain service for ingestion state management.

This module contains pure business logic for managing ingestion state,
separated from infrastructure concerns.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ...core.entities import IngestionState, IngestionDecision


class StateManagementService:
    """
    Domain service for managing ingestion state.
    
    This service contains pure business logic for state management, with no
    dependencies on external systems or infrastructure.
    """
    
    @staticmethod
    def determine_ingestion_state(
        status_data: Dict[str, Any],
        staleness_threshold_seconds: int
    ) -> IngestionState:
        """
        Determine ingestion state from status data.
        
        Args:
            status_data: Status data from storage
            staleness_threshold_seconds: Threshold for considering state stale
            
        Returns:
            IngestionState: Current ingestion state
        """
        status_str = status_data.get('status', 'unknown')
        timestamp_str = status_data.get('timestamp')
        
        # Map string status to enum
        status_mapping = {
            'not_started': IngestionState.NOT_STARTED,
            'in_progress': IngestionState.IN_PROGRESS,
            'completed': IngestionState.COMPLETED,
            'failed': IngestionState.FAILED,
            'unknown': IngestionState.UNKNOWN
        }
        
        state = status_mapping.get(status_str, IngestionState.UNKNOWN)
        
        # Check for stale in-progress state
        if state == IngestionState.IN_PROGRESS and timestamp_str:
            if StateManagementService._is_timestamp_stale(timestamp_str, staleness_threshold_seconds):
                return IngestionState.UNKNOWN
        
        return state
    
    @staticmethod
    def make_ingestion_decision(
        current_state: IngestionState,
        existing_classes: List[str],
        force_reingest: bool,
        is_interactive: bool,
        timestamp: Optional[str] = None,
        is_stale: bool = False
    ) -> IngestionDecision:
        """
        Make decision about whether to run ingestion.
        
        Args:
            current_state: Current ingestion state
            existing_classes: List of existing classes
            force_reingest: Whether force re-ingestion is requested
            is_interactive: Whether running in interactive mode
            timestamp: Optional timestamp of last state change
            is_stale: Whether current state is stale
            
        Returns:
            IngestionDecision: Decision with reasoning
        """
        # Handle force reingest
        if force_reingest:
            return IngestionDecision(
                should_run=True,
                reason="Force re-ingestion requested",
                current_state=current_state,
                force_required=False,
                existing_classes=existing_classes,
                timestamp=timestamp
            )
        
        # Handle completed state
        if current_state == IngestionState.COMPLETED:
            return IngestionDecision(
                should_run=False,
                reason="Ingestion already completed",
                current_state=current_state,
                force_required=True,
                existing_classes=existing_classes,
                timestamp=timestamp
            )
        
        # Handle in-progress state
        if current_state == IngestionState.IN_PROGRESS:
            if not is_stale:
                return IngestionDecision(
                    should_run=False,
                    reason="Ingestion currently in progress and not stale",
                    current_state=current_state,
                    force_required=True,
                    existing_classes=existing_classes,
                    timestamp=timestamp,
                    is_stale=False
                )
            else:
                return IngestionDecision(
                    should_run=True,
                    reason="Stale in-progress ingestion detected, proceeding with new ingestion",
                    current_state=current_state,
                    force_required=False,
                    existing_classes=existing_classes,
                    timestamp=timestamp,
                    is_stale=True
                )
        
        # Handle existing data without force reingest
        if existing_classes and not force_reingest:
            if not is_interactive:
                return IngestionDecision(
                    should_run=False,
                    reason=f"Non-interactive mode with existing data for classes: {', '.join(existing_classes)}",
                    current_state=current_state,
                    force_required=True,
                    existing_classes=existing_classes,
                    timestamp=timestamp
                )
            else:
                return IngestionDecision(
                    should_run=True,
                    reason=f"Interactive mode with existing data for classes: {', '.join(existing_classes)}",
                    current_state=current_state,
                    force_required=False,
                    existing_classes=existing_classes,
                    timestamp=timestamp
                )
        
        # Default case: proceed with ingestion
        return IngestionDecision(
            should_run=True,
            reason="No existing data or force re-ingestion requested",
            current_state=current_state,
            force_required=False,
            existing_classes=existing_classes,
            timestamp=timestamp
        )
    
    @staticmethod
    def _is_timestamp_stale(timestamp_str: str, threshold_seconds: int) -> bool:
        """
        Check if a timestamp is stale.
        
        Args:
            timestamp_str: ISO format timestamp string
            threshold_seconds: Threshold in seconds
            
        Returns:
            bool: True if timestamp is stale
        """
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.utcnow() - timestamp
            return age.total_seconds() > threshold_seconds
        except (ValueError, TypeError):
            return True 