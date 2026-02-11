"""
Ingestion orchestrator for ESCO data.

Coordinates the full 12-step ESCO ingestion pipeline:
schema setup, 5 entity types, and 6 relation types.
"""

import logging
from datetime import datetime
from typing import Optional, Callable, Dict, Any

from .esco_data_reader import ESCODataReader
from .entity_ingestor import EntityIngestor
from .relation_builder import RelationBuilder

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """Orchestrates the complete ESCO ingestion process."""

    def __init__(
        self,
        client,
        data_dir: str,
        batch_size: int = 100,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            client: WeaviateClient instance
            data_dir: Directory containing ESCO CSV files
            batch_size: Batch size for CSV processing
            progress_callback: Optional progress callback
        """
        self.client = client
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.progress_callback = progress_callback

    def _update_heartbeat(self, step_name: str, processed: int = 0, total: int = 0) -> None:
        """Update heartbeat metadata for a given step."""
        try:
            self.client.set_ingestion_metadata(
                status="in_progress",
                details={
                    "step": step_name,
                    "progress": f"{processed}/{total}" if total else step_name,
                    "last_heartbeat": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            logger.debug(f"Heartbeat update failed: {e}")

    def run_complete_ingestion(self) -> Dict[str, Any]:
        """
        Run the complete 12-step ESCO ingestion pipeline.

        Returns:
            Dictionary with step completion status
        """
        logger.info("Starting complete ESCO ingestion pipeline")
        results: Dict[str, Any] = {}

        data_reader = ESCODataReader(self.data_dir, self.batch_size)
        entity_ingestor = EntityIngestor(
            self.client, data_reader,
            heartbeat_callback=self._update_heartbeat
        )
        relation_builder = RelationBuilder(self.client, data_reader)

        steps = [
            ("ensure_schema", lambda: self.client.ensure_schema()),
            ("ingest_isco_groups", entity_ingestor.ingest_isco_groups),
            ("ingest_occupations", entity_ingestor.ingest_occupations),
            ("ingest_skills", entity_ingestor.ingest_skills),
            ("ingest_skill_groups", entity_ingestor.ingest_skill_groups),
            ("ingest_skill_collections", entity_ingestor.ingest_skill_collections),
            ("create_skill_relations", relation_builder.create_skill_relations),
            ("create_hierarchical_relations", relation_builder.create_hierarchical_relations),
            ("create_isco_group_relations", relation_builder.create_isco_group_relations),
            ("create_skill_collection_relations", relation_builder.create_skill_collection_relations),
            ("create_skill_skill_relations", relation_builder.create_skill_skill_relations),
            ("create_broader_skill_relations", relation_builder.create_broader_skill_relations),
        ]

        for idx, (step_name, step_func) in enumerate(steps, 1):
            logger.info(f"Step {idx}/{len(steps)}: {step_name}")
            self._update_heartbeat(step_name)
            try:
                step_func()
                results[step_name] = "completed"
            except Exception as e:
                logger.error(f"Step {step_name} failed: {e}")
                results[step_name] = f"failed: {e}"
                raise

        logger.info("Complete ESCO ingestion pipeline finished")
        return results
