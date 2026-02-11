"""
Initialization module for ESCO ingestion process.
This module handles the initialization of the ingestion process.
"""

import logging
import sys
import os
import time
from pathlib import Path
from src.infrastructure.database.weaviate.weaviate_client import WeaviateClient
from src.esco_ingest import WeaviateIngestor

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
    Initialize the ESCO ingestion process.
    This function sets up the necessary environment and configurations for ingestion.
    """
    logger.info("Starting ESCO ingestion initialization")
    
    # Create necessary directories if they don't exist
    data_dir = Path("/app/data/esco")
    logs_dir = Path("/app/logs")
    
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get Weaviate URL from environment variable
        weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
        
        # Initialize Weaviate client with proper timeout configuration
        client = WeaviateClient(
            url=weaviate_url,
            timeout_config=(5.0, 60.0)  # (connect timeout, read timeout) in seconds
        )
        
        # Wait for Weaviate to become available
        if not wait_for_weaviate(client):
            logger.error("Failed to connect to Weaviate after multiple attempts")
            return 3  # Exit code for initialization failure
        
        # Initialize the ingestor with the client directly
        ingestor = WeaviateIngestor(client=client)
        
        # Initialize schema if needed
        ingestor.initialize_schema()
        
        # Start the ingestion process
        logger.info("Starting ESCO data ingestion")
        ingestor.run_simple_ingestion()
        
        logger.info("Initialization and ingestion completed successfully")
        return 0  # Success
        
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        return 3  # Exit code for initialization failure

if __name__ == "__main__":
    sys.exit(init_ingestion()) 