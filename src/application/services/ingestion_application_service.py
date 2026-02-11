"""
Application service for ingestion operations.

This service orchestrates domain services and infrastructure to implement
the IngestionServiceInterface contract.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from ...core.interfaces import (
    RepositoryInterface,
    IngestionServiceInterface,
    VectorDatabaseClientInterface
)
from ...core.entities import (
    IngestionState,
    IngestionDecision,
    IngestionProgress,
    IngestionResult,
    ValidationResult,
    IngestionConfig
)
from ...domain.ingestion.ingestion_domain_service import IngestionDomainService
from ...domain.ingestion.state_management_service import StateManagementService

logger = logging.getLogger(__name__)


class IngestionApplicationService(IngestionServiceInterface):
    """
    Application service for ingestion operations.

    Implements all 6 methods from IngestionServiceInterface by delegating
    to domain services and infrastructure clients.
    """

    def __init__(
        self,
        repository: RepositoryInterface,
        client: VectorDatabaseClientInterface,
        ingestion_domain_service: IngestionDomainService,
        state_management_service: StateManagementService,
        config: IngestionConfig,
        ingestor=None
    ):
        """
        Initialize the service.

        Args:
            repository: Document repository
            client: Weaviate database client
            ingestion_domain_service: Domain service for ingestion logic
            state_management_service: Domain service for state management
            config: Ingestion configuration
            ingestor: Legacy ingestor for delegation (WeaviateIngestor)
        """
        self.repository = repository
        self.client = client
        self.ingestion_domain_service = ingestion_domain_service
        self.state_management_service = state_management_service
        self.config = config
        self.ingestor = ingestor

    def get_current_state(self) -> IngestionState:
        """Get the current ingestion state."""
        status_data = self.client.get_ingestion_status()
        return self.ingestion_domain_service.determine_ingestion_state(
            status_data, self.config
        )

    def should_run_ingestion(self, force_reingest: bool = False) -> IngestionDecision:
        """Determine whether ingestion should run."""
        status_data = self.client.get_ingestion_status()
        raw_status = status_data.get("status", "unknown")
        timestamp = status_data.get("timestamp")

        # Check staleness on the raw status BEFORE state resolution
        # (determine_ingestion_state maps stale in_progress -> UNKNOWN)
        is_stale = False
        if raw_status == "in_progress" and timestamp:
            is_stale = StateManagementService._is_timestamp_stale(
                timestamp, self.config.staleness_threshold_seconds
            )

        # Use IN_PROGRESS for the decision when stale, so the domain
        # service can reason about staleness properly
        if is_stale:
            current_state = IngestionState.IN_PROGRESS
        else:
            current_state = self.ingestion_domain_service.determine_ingestion_state(
                status_data, self.config
            )

        # Check which classes already have data
        existing_classes = []
        for class_name in self.config.classes_to_ingest:
            try:
                repo = self.client.get_repository(class_name)
                if repo.count_objects() > 0:
                    existing_classes.append(class_name)
            except Exception:
                pass

        # Override force_reingest from config or argument
        effective_force = force_reingest or self.config.force_reingest

        # Temporarily set force_reingest on config for the domain service
        original_force = self.config.force_reingest
        self.config.force_reingest = effective_force
        try:
            decision = self.ingestion_domain_service.make_ingestion_decision(
                current_state=current_state,
                existing_classes=existing_classes,
                config=self.config,
                timestamp=timestamp,
                is_stale=is_stale
            )
        finally:
            self.config.force_reingest = original_force

        return decision

    def validate_prerequisites(self) -> ValidationResult:
        """Validate all prerequisites for ingestion."""
        result = ValidationResult(is_valid=True)

        # Check Weaviate connectivity
        result.checks_performed.append("weaviate_connectivity")
        try:
            if not self.client.is_connected():
                result.add_error(
                    "Cannot connect to Weaviate", "weaviate_connectivity"
                )
                return result
            result.add_success("Weaviate is reachable", "weaviate_connectivity")
        except Exception as e:
            result.add_error(
                f"Connection failed: {str(e)}", "weaviate_connectivity"
            )
            return result

        # Ensure schema exists
        result.checks_performed.append("schema_validation")
        try:
            self.client.ensure_schema()
            result.add_success("Schema is ready", "schema_validation")
        except Exception as e:
            result.add_error(
                f"Schema setup failed: {str(e)}", "schema_validation"
            )
            return result

        # Validate config and data files via domain service
        required_files = [
            "occupations_en.csv",
            "skills_en.csv",
            "ISCOGroups_en.csv",
            "broaderRelationsOccPillar_en.csv",
            "occupationSkillRelations_en.csv",
        ]
        domain_result = self.ingestion_domain_service.validate_ingestion_prerequisites(
            self.config, required_files
        )
        result.checks_performed.extend(domain_result.checks_performed)
        result.errors.extend(domain_result.errors)
        result.warnings.extend(domain_result.warnings)
        result.details.update(domain_result.details)
        if domain_result.errors:
            result.is_valid = False

        return result

    def run_ingestion(
        self,
        progress_callback: Optional[Callable[[IngestionProgress], None]] = None
    ) -> IngestionResult:
        """Run the ingestion process."""
        start_time = datetime.utcnow()
        total_steps = 12  # schema + 5 entities + 6 relations

        # Mark ingestion as in-progress
        try:
            self.client.set_ingestion_metadata(
                status="in_progress",
                details={
                    "started_at": start_time.isoformat(),
                    "last_heartbeat": start_time.isoformat(),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to set initial metadata: {e}")

        try:
            if self.ingestor:
                self.ingestor.run_simple_ingestion()
            else:
                # Try the new orchestrator, fall back to error
                try:
                    from ...infrastructure.ingestion.ingestion_orchestrator import (
                        IngestionOrchestrator,
                    )
                    orchestrator = IngestionOrchestrator(
                        client=self.client,
                        data_dir=self.config.data_dir,
                        batch_size=self.config.batch_size,
                        progress_callback=progress_callback,
                    )
                    orchestrator.run_complete_ingestion()
                except ImportError:
                    raise RuntimeError(
                        "No ingestor provided and IngestionOrchestrator not available"
                    )

            end_time = datetime.utcnow()

            # Mark completed
            self.client.set_ingestion_metadata(
                status="completed",
                details={
                    "completed_at": end_time.isoformat(),
                    "started_at": start_time.isoformat(),
                }
            )

            return IngestionResult(
                success=True,
                steps_completed=total_steps,
                total_steps=total_steps,
                start_time=start_time,
                end_time=end_time,
                final_state=IngestionState.COMPLETED,
                last_completed_step="create_broader_skill_relations",
            )

        except Exception as e:
            end_time = datetime.utcnow()
            logger.error(f"Ingestion failed: {e}")

            # Mark failed
            try:
                self.client.set_ingestion_metadata(
                    status="failed",
                    details={
                        "error": str(e),
                        "failed_at": end_time.isoformat(),
                        "started_at": start_time.isoformat(),
                    }
                )
            except Exception:
                pass

            return IngestionResult(
                success=False,
                steps_completed=0,
                total_steps=total_steps,
                errors=[str(e)],
                start_time=start_time,
                end_time=end_time,
                final_state=IngestionState.FAILED,
            )

    def verify_completion(self) -> ValidationResult:
        """Verify that ingestion completed successfully."""
        result = ValidationResult(is_valid=True)
        result.checks_performed.append("completion_verification")

        current_state = self.get_current_state()
        if current_state != IngestionState.COMPLETED:
            result.add_error(
                f"Ingestion state is {current_state.value}, expected completed",
                "state_check"
            )
            return result

        result.add_success("Ingestion state is completed", "state_check")

        # Check that each class has data
        for class_name in self.config.classes_to_ingest:
            try:
                repo = self.client.get_repository(class_name)
                count = repo.count_objects()
                if count > 0:
                    result.add_success(
                        f"{class_name}: {count} objects", class_name
                    )
                else:
                    result.add_warning(
                        f"{class_name}: 0 objects", class_name
                    )
            except Exception as e:
                result.add_warning(
                    f"{class_name}: could not count objects ({e})", class_name
                )

        return result

    def get_ingestion_metrics(self) -> Dict[str, Any]:
        """Get metrics about the ingestion process."""
        metrics: Dict[str, Any] = {"class_counts": {}, "total_objects": 0}

        for class_name in self.config.classes_to_ingest:
            try:
                repo = self.client.get_repository(class_name)
                count = repo.count_objects()
                metrics["class_counts"][class_name] = count
                metrics["total_objects"] += count
            except Exception:
                metrics["class_counts"][class_name] = -1

        # Include current ingestion status
        status_data = self.client.get_ingestion_status()
        metrics["status"] = status_data.get("status", "unknown")
        metrics["timestamp"] = status_data.get("timestamp")

        return metrics


# Backwards-compatible alias
IngestionService = IngestionApplicationService
