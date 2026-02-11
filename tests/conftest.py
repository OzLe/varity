"""
Test configuration and fixtures for ESCO ingestion tests.
"""

import pytest
from typing import Dict, Any
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.core.entities.ingestion_entity import IngestionConfig
from src.application.services.ingestion_application_service import (
    IngestionApplicationService,
    IngestionService,
)
from src.domain.ingestion.ingestion_domain_service import IngestionDomainService
from src.domain.ingestion.state_management_service import StateManagementService


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test configuration with shorter timeouts for testing."""
    return {
        "weaviate": {
            "url": "http://test:8080",
            "batch_size": 100,
        },
        "app": {
            "data_dir": "test_data",
            "staleness_threshold_seconds": 10,
        },
    }


@pytest.fixture
def ingestion_config(test_config) -> IngestionConfig:
    """IngestionConfig instance for testing."""
    return IngestionConfig(
        config_path="test_config.yaml",
        profile="test",
        data_dir="test_data",
        batch_size=100,
        staleness_threshold_seconds=10,
        raw_config=test_config,
    )


@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    repo = Mock()
    repo.count.return_value = 0
    return repo


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client for testing."""
    client = Mock()

    # Connection
    client.is_connected.return_value = True

    # Schema
    client.ensure_schema.return_value = None

    # Ingestion status — default to "not started"
    client.get_ingestion_status.return_value = {
        "status": "unknown",
        "timestamp": None,
        "details": {},
    }

    # set_ingestion_metadata is a no-op in tests
    client.set_ingestion_metadata.return_value = None

    # check_object_exists
    client.check_object_exists.return_value = False

    # get_repository returns a proxy mock whose count_objects returns 0
    def _make_repo_proxy(class_name):
        proxy = Mock()
        proxy.count_objects.return_value = 0
        return proxy

    client.get_repository.side_effect = _make_repo_proxy

    return client


@pytest.fixture
def mock_ingestor():
    """Mock legacy WeaviateIngestor."""
    ingestor = Mock()
    ingestor.run_simple_ingestion.return_value = None
    return ingestor


@pytest.fixture
def ingestion_service(
    mock_repository,
    mock_weaviate_client,
    ingestion_config,
    mock_ingestor,
):
    """Create an IngestionApplicationService with all dependencies mocked."""
    return IngestionApplicationService(
        repository=mock_repository,
        client=mock_weaviate_client,
        ingestion_domain_service=IngestionDomainService(),
        state_management_service=StateManagementService(),
        config=ingestion_config,
        ingestor=mock_ingestor,
    )


@pytest.fixture
def mock_progress():
    """Create a mock progress object for testing."""
    return {
        "current_step": "Processing occupations",
        "step_number": 1,
        "total_steps": 12,
        "items_processed": 50,
        "total_items": 100,
        "started_at": datetime.utcnow().isoformat(),
        "heartbeat": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_stale_progress():
    """Create a mock stale progress object for testing."""
    return {
        "current_step": "Processing occupations",
        "step_number": 1,
        "total_steps": 12,
        "items_processed": 50,
        "total_items": 100,
        "started_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "heartbeat": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
    }
