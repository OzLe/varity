"""
Entity ingestor for ESCO data.

Handles batch insertion of ESCO entity types (occupations, skills,
ISCO groups, skill groups, skill collections) into Weaviate.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Callable

from .esco_data_reader import ESCODataReader

logger = logging.getLogger(__name__)


class EntityIngestor:
    """Ingests ESCO entity records into the vector database."""

    def __init__(
        self,
        client,
        data_reader: ESCODataReader,
        heartbeat_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        Initialize the entity ingestor.

        Args:
            client: WeaviateClient instance
            data_reader: ESCODataReader for CSV processing
            heartbeat_callback: Optional callback(step_name, processed, total)
        """
        self.client = client
        self.data_reader = data_reader
        self.heartbeat_callback = heartbeat_callback

    def _make_heartbeat(self, step_name: str) -> Optional[Callable[[int, int], None]]:
        """Create a heartbeat callback bound to a step name."""
        if not self.heartbeat_callback:
            return None

        def callback(processed: int, total: int) -> None:
            self.heartbeat_callback(step_name, processed, total)

        return callback

    def ingest_isco_groups(self) -> None:
        """Ingest ISCO groups into Weaviate."""
        logger.info("Ingesting ISCO groups...")

        def process_batch(batch):
            objects = []
            uuids = []
            for record in batch.to_dict("records"):
                try:
                    data = {
                        "uri": record["conceptUri"],
                        "code": record.get("code", ""),
                        "preferredLabel_en": record.get("preferredLabel", ""),
                        "description_en": record.get("description", ""),
                        "iscoLevel": record.get("iscoLevel", ""),
                    }
                    data = {k: v for k, v in data.items() if v is not None and v != ""}
                    uuid = data["uri"].split("/")[-1]
                    objects.append(data)
                    uuids.append(uuid)
                except Exception as e:
                    logger.error(f"Failed to prepare ISCO group: {e}")
            if objects:
                self.client.batch_add_objects("ISCOGroup", objects, uuids)

        self.data_reader.process_csv_in_batches(
            "ISCOGroups_en.csv", process_batch,
            self._make_heartbeat("ingest_isco_groups")
        )
        logger.info("ISCO group ingestion completed")

    def ingest_occupations(self) -> None:
        """Ingest occupations from CSV."""
        logger.info("Starting occupation ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    objects.append({
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "definition_en": record.get("definition_en", ""),
                        "code": record.get("code", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else [],
                    })
                except Exception as e:
                    logger.error(f"Error preparing occupation: {e}")
            if objects:
                self.client.batch_add_objects("Occupation", objects)

        self.data_reader.process_csv_in_batches(
            "occupations_en.csv", process_batch,
            self._make_heartbeat("ingest_occupations")
        )
        logger.info("Occupation ingestion completed")

    def ingest_skills(self) -> None:
        """Ingest skills from CSV."""
        logger.info("Starting skill ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    objects.append({
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "skillType": record.get("skillType", ""),
                        "reuseLevel": record.get("reuseLevel", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else [],
                    })
                except Exception as e:
                    logger.error(f"Error preparing skill: {e}")
            if objects:
                self.client.batch_add_objects("Skill", objects)

        self.data_reader.process_csv_in_batches(
            "skills_en.csv", process_batch,
            self._make_heartbeat("ingest_skills")
        )
        logger.info("Skill ingestion completed")

    def ingest_skill_groups(self) -> None:
        """Ingest skill groups from CSV."""
        logger.info("Starting skill group ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    objects.append({
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else [],
                    })
                except Exception as e:
                    logger.error(f"Error preparing skill group: {e}")
            if objects:
                self.client.batch_add_objects("SkillGroup", objects)

        self.data_reader.process_csv_in_batches(
            "skillGroups_en.csv", process_batch,
            self._make_heartbeat("ingest_skill_groups")
        )
        logger.info("Skill group ingestion completed")

    def ingest_skill_collections(self) -> None:
        """Ingest skill collections from CSV."""
        logger.info("Starting skill collection ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    objects.append({
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else [],
                    })
                except Exception as e:
                    logger.error(f"Error preparing skill collection: {e}")
            if objects:
                self.client.batch_add_objects("SkillCollection", objects)

        self.data_reader.process_csv_in_batches(
            "conceptSchemes_en.csv", process_batch,
            self._make_heartbeat("ingest_skill_collections")
        )
        logger.info("Skill collection ingestion completed")
