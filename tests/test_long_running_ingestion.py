"""
Tests for long-running ingestion scenarios.

Covers heartbeat-based staleness detection, state transitions,
completion verification, and metrics collection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.core.entities.ingestion_entity import (
    IngestionState,
    IngestionConfig,
)
from src.application.services.ingestion_application_service import IngestionApplicationService
from src.domain.ingestion.ingestion_domain_service import IngestionDomainService
from src.domain.ingestion.state_management_service import StateManagementService


class TestLongRunningIngestion:
    """Test suite for long-running ingestion scenarios."""

    def _make_service(self, mock_weaviate_client, mock_ingestor=None):
        """Helper to create a service instance."""
        config = IngestionConfig(
            config_path="test_config.yaml",
            profile="test",
            data_dir="test_data",
            batch_size=100,
            staleness_threshold_seconds=10,
        )
        ingestor = mock_ingestor or Mock()
        ingestor.run_simple_ingestion.return_value = None
        return IngestionApplicationService(
            repository=Mock(),
            client=mock_weaviate_client,
            ingestion_domain_service=IngestionDomainService(),
            state_management_service=StateManagementService(),
            config=config,
            ingestor=ingestor,
        )

    def test_heartbeat_based_staleness_detection(self, mock_weaviate_client):
        """Old timestamp -> state resolves to UNKNOWN, should_run is True."""
        old_timestamp = (datetime.utcnow() - timedelta(hours=3)).isoformat()
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "in_progress",
            "timestamp": old_timestamp,
            "details": {},
        }

        service = self._make_service(mock_weaviate_client)
        decision = service.should_run_ingestion()
        assert decision.should_run

    def test_ingestion_runs_with_valid_prerequisites(self, mock_weaviate_client, tmp_path):
        """Validate prerequisites then run ingestion successfully."""
        mock_weaviate_client.is_connected.return_value = True
        mock_weaviate_client.ensure_schema.return_value = None

        service = self._make_service(mock_weaviate_client)

        # Config validation checks that config_path and data_dir exist on disk
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("default: {}")
        service.config.config_path = str(config_file)
        service.config.data_dir = str(tmp_path)

        validation = service.validate_prerequisites()
        assert validation.is_valid

        result = service.run_ingestion()
        assert result.success

    def test_ingestion_state_transitions(self, mock_weaviate_client):
        """State goes NOT_STARTED -> run -> COMPLETED."""
        # Start as not_started
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "not_started",
            "timestamp": None,
            "details": {},
        }

        service = self._make_service(mock_weaviate_client)

        state_before = service.get_current_state()
        assert state_before == IngestionState.NOT_STARTED

        result = service.run_ingestion()
        assert result.success
        assert result.final_state == IngestionState.COMPLETED

    def test_verify_completion_with_data(self, mock_weaviate_client):
        """Verify completion when classes have data."""
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        def _repo_with_data(class_name):
            proxy = Mock()
            proxy.count_objects.return_value = 200
            return proxy

        mock_weaviate_client.get_repository.side_effect = _repo_with_data

        service = self._make_service(mock_weaviate_client)
        validation = service.verify_completion()
        assert validation.is_valid

    def test_metrics_collection(self, mock_weaviate_client):
        """Verify metric keys are present."""
        def _repo_with_count(class_name):
            proxy = Mock()
            proxy.count_objects.return_value = 42
            return proxy

        mock_weaviate_client.get_repository.side_effect = _repo_with_count
        mock_weaviate_client.get_ingestion_status.return_value = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        service = self._make_service(mock_weaviate_client)
        metrics = service.get_ingestion_metrics()
        assert "total_objects" in metrics
        assert "class_counts" in metrics
        assert "status" in metrics
        assert metrics["total_objects"] > 0
