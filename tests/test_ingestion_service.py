"""
Tests for the ingestion application service layer.

All tests exercise the 6 methods from IngestionServiceInterface.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.core.entities.ingestion_entity import (
    IngestionState,
    IngestionConfig,
    IngestionResult,
)


class TestIngestionService:
    """Test suite for IngestionApplicationService."""

    # ------------------------------------------------------------------ #
    # should_run_ingestion
    # ------------------------------------------------------------------ #

    def test_should_run_ingestion_when_not_started(
        self, ingestion_service, mock_weaviate_client
    ):
        """Ingestion should run when state is unknown / not started."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "not_started",
            "timestamp": None,
            "details": {},
        }

        decision = ingestion_service.should_run_ingestion()
        assert decision.should_run
        assert decision.current_state == IngestionState.NOT_STARTED

    def test_should_not_run_ingestion_when_completed(
        self, ingestion_service, mock_weaviate_client
    ):
        """Ingestion should not run when already completed."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        decision = ingestion_service.should_run_ingestion()
        assert not decision.should_run
        assert decision.current_state == IngestionState.COMPLETED
        assert "already completed" in decision.reason.lower()

    def test_should_run_ingestion_when_stale(
        self, ingestion_service, mock_weaviate_client
    ):
        """Ingestion should run when previous run is stale."""
        old_timestamp = (datetime.utcnow() - timedelta(hours=3)).isoformat()
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "in_progress",
            "timestamp": old_timestamp,
            "details": {},
        }

        decision = ingestion_service.should_run_ingestion()
        assert decision.should_run
        assert decision.is_stale
        assert "stale" in decision.reason.lower()

    def test_should_not_run_ingestion_when_active(
        self, ingestion_service, mock_weaviate_client
    ):
        """Ingestion should not run when actively in progress."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "in_progress",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        decision = ingestion_service.should_run_ingestion()
        assert not decision.should_run
        assert "in progress" in decision.reason.lower()

    def test_force_reingest_overrides_checks(
        self, ingestion_service, mock_weaviate_client
    ):
        """Force reingest should override completed state."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        decision = ingestion_service.should_run_ingestion(force_reingest=True)
        assert decision.should_run
        assert "force" in decision.reason.lower()

    # ------------------------------------------------------------------ #
    # validate_prerequisites
    # ------------------------------------------------------------------ #

    def test_validate_prerequisites(
        self, ingestion_service, mock_weaviate_client, tmp_path
    ):
        """Successful prerequisite validation."""
        mock_weaviate_client.is_connected.return_value = True
        mock_weaviate_client.ensure_schema.return_value = None

        # Config validation checks that config_path and data_dir exist on disk
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("default: {}")
        ingestion_service.config.config_path = str(config_file)
        ingestion_service.config.data_dir = str(tmp_path)

        validation = ingestion_service.validate_prerequisites()
        assert validation.is_valid
        assert "weaviate_connectivity" in validation.checks_performed

    def test_validate_prerequisites_fails_when_disconnected(
        self, ingestion_service, mock_weaviate_client
    ):
        """Prerequisite validation fails when Weaviate is unreachable."""
        mock_weaviate_client.is_connected.return_value = False

        validation = ingestion_service.validate_prerequisites()
        assert not validation.is_valid
        assert any("connect" in e.lower() for e in validation.errors)

    def test_validate_prerequisites_fails_on_schema_error(
        self, ingestion_service, mock_weaviate_client
    ):
        """Prerequisite validation fails when schema setup raises."""
        mock_weaviate_client.is_connected.return_value = True
        mock_weaviate_client.ensure_schema.side_effect = Exception("Connection failed")

        validation = ingestion_service.validate_prerequisites()
        assert not validation.is_valid
        assert any("connection failed" in e.lower() for e in validation.errors)

    # ------------------------------------------------------------------ #
    # run_ingestion
    # ------------------------------------------------------------------ #

    def test_run_ingestion_success(
        self, ingestion_service, mock_ingestor
    ):
        """Successful ingestion run."""
        result = ingestion_service.run_ingestion()
        assert result.success
        assert result.final_state == IngestionState.COMPLETED
        mock_ingestor.run_simple_ingestion.assert_called_once()

    def test_run_ingestion_handles_failure(
        self, ingestion_service, mock_ingestor
    ):
        """Failed ingestion returns error result."""
        mock_ingestor.run_simple_ingestion.side_effect = Exception("Step failed")

        result = ingestion_service.run_ingestion()
        assert not result.success
        assert result.final_state == IngestionState.FAILED
        assert any("step failed" in e.lower() for e in result.errors)

    # ------------------------------------------------------------------ #
    # verify_completion
    # ------------------------------------------------------------------ #

    def test_verify_completion_success(
        self, ingestion_service, mock_weaviate_client
    ):
        """Verification passes when state is completed and classes have data."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        def _repo_with_data(class_name):
            proxy = Mock()
            proxy.count_objects.return_value = 100
            return proxy

        mock_weaviate_client.get_repository.side_effect = _repo_with_data

        validation = ingestion_service.verify_completion()
        assert validation.is_valid

    def test_verify_completion_fails_when_not_completed(
        self, ingestion_service, mock_weaviate_client
    ):
        """Verification fails when state is not completed."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "in_progress",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        validation = ingestion_service.verify_completion()
        assert not validation.is_valid

    # ------------------------------------------------------------------ #
    # get_ingestion_metrics
    # ------------------------------------------------------------------ #

    def test_get_ingestion_metrics(
        self, ingestion_service, mock_weaviate_client
    ):
        """Metrics include total_objects and class counts."""
        def _repo_with_count(class_name):
            proxy = Mock()
            proxy.count_objects.return_value = 50
            return proxy

        mock_weaviate_client.get_repository.side_effect = _repo_with_count
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        metrics = ingestion_service.get_ingestion_metrics()
        assert "total_objects" in metrics
        assert metrics["total_objects"] > 0
        assert "class_counts" in metrics
        assert metrics["status"] == "completed"
