"""
Initialization module for ESCO ingestion process.

Tries the new IngestionOrchestrator first, falls back to legacy
WeaviateIngestor for safety.
"""

import logging
import sys
import os
import time
from pathlib import Path

from src.infrastructure.database.weaviate.weaviate_client import WeaviateClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_weaviate(client: WeaviateClient, max_retries: int = 30, retry_interval: int = 2) -> bool:
    """
    Wait for Weaviate to become available.

    Args:
        client: Weaviate client
        max_retries: Maximum number of retry attempts
        retry_interval: Time between retries in seconds

    Returns:
        bool: True if Weaviate is available, False otherwise
    """
    for attempt in range(max_retries):
        if client.is_connected():
            return True
        logger.info(f"Waiting for Weaviate to become available (attempt {attempt + 1}/{max_retries})")
        time.sleep(retry_interval)
    return False


def init_ingestion():
    """
    Initialize and run the ESCO ingestion process.

    Uses IngestionOrchestrator when available, falls back to
    WeaviateIngestor for backwards compatibility.
    """
    logger.info("Starting ESCO ingestion initialization")

    # Create necessary directories if they don't exist
    data_dir = Path("/app/data/esco")
    logs_dir = Path("/app/logs")

    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Get Weaviate connection settings from environment
        weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
        weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

        # Initialize Weaviate client with proper timeout configuration
        import weaviate as _weaviate
        auth = _weaviate.AuthApiKey(api_key=weaviate_api_key) if weaviate_api_key else None
        client = WeaviateClient(
            url=weaviate_url,
            auth_client_secret=auth,
            timeout_config=(5.0, 60.0)
        )

        # Wait for Weaviate to become available
        if not wait_for_weaviate(client):
            logger.error("Failed to connect to Weaviate after multiple attempts")
            return 3

        # Try the new orchestrator first
        try:
            from src.infrastructure.ingestion.ingestion_orchestrator import IngestionOrchestrator
            logger.info("Using IngestionOrchestrator for ingestion")
            client.ensure_schema()
            orchestrator = IngestionOrchestrator(
                client=client,
                data_dir=str(data_dir),
                batch_size=100,
            )
            orchestrator.run_complete_ingestion()
            logger.info("Orchestrator ingestion completed successfully")
            return 0
        except ImportError:
            logger.info("IngestionOrchestrator not available, falling back to legacy WeaviateIngestor")
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}, falling back to legacy WeaviateIngestor")

        # Fallback to legacy ingestor
        from src.esco_ingest import WeaviateIngestor
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            ingestor = WeaviateIngestor(client=client)
        ingestor.initialize_schema()
        ingestor.run_simple_ingestion()

        logger.info("Initialization and ingestion completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        return 3


if __name__ == "__main__":
    sys.exit(init_ingestion())
