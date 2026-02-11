"""
Relation builder for ESCO data.

Creates cross-references between ESCO entities in Weaviate using
pre-fetched UUID caches for efficient lookups.
"""

import logging
from typing import Set

import pandas as pd
from tqdm import tqdm

from .esco_data_reader import ESCODataReader

logger = logging.getLogger(__name__)


class RelationBuilder:
    """Builds cross-reference relations between ESCO entities."""

    def __init__(self, client, data_reader: ESCODataReader):
        """
        Initialize the relation builder.

        Args:
            client: WeaviateClient instance
            data_reader: ESCODataReader for CSV access
        """
        self.client = client
        self.data_reader = data_reader
        self._uuid_cache: dict[str, Set[str]] = {}

    def _prefetch_uuids(self, class_name: str) -> Set[str]:
        """Pre-fetch all UUIDs for a class (cached)."""
        if class_name not in self._uuid_cache:
            logger.info(f"Pre-fetching UUIDs for {class_name}...")
            uuids = set(self.client.get_all_uuids(class_name))
            logger.info(f"Pre-fetched {len(uuids)} UUIDs for {class_name}")
            self._uuid_cache[class_name] = uuids
        return self._uuid_cache[class_name]

    def create_skill_relations(self) -> None:
        """Create occupation-skill relations."""
        df = self.data_reader.read_csv("occupationSkillRelations_en.csv")
        if df is None or len(df) == 0:
            logger.warning("No occupation-skill relations found - skipping.")
            return

        logger.info("Creating occupation-skill relations...")
        occupation_uuids = self._prefetch_uuids("Occupation")
        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Occupation-Skill Relations", unit="rel"):
            try:
                occ_uuid = record["occupationUri"].split("/")[-1]
                skill_uuid = record["skillUri"].split("/")[-1]
                relation_type = record.get("relationType", "related")

                if occ_uuid not in occupation_uuids or skill_uuid not in skill_uuids:
                    skipped += 1
                    continue

                ref_prop = (
                    "hasEssentialSkill" if relation_type == "essential"
                    else "hasOptionalSkill" if relation_type == "optional"
                    else "hasEssentialSkill"
                )
                refs_batch.append({
                    "from_class": "Occupation", "from_uuid": occ_uuid,
                    "ref_property": ref_prop,
                    "to_class": "Skill", "to_uuid": skill_uuid,
                })
            except Exception as e:
                logger.error(f"Failed to prepare occupation-skill relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} occupation-skill references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Occupation-skill relations completed")

    def create_hierarchical_relations(self) -> None:
        """Create hierarchical relations between occupations."""
        df = self.data_reader.read_csv("broaderRelationsOccPillar_en.csv")
        if df is None:
            return

        df = ESCODataReader.standardize_hierarchy_columns(df)
        if "broaderUri" not in df.columns or "narrowerUri" not in df.columns:
            logger.warning("Required hierarchy columns not found - skipping.")
            return
        if len(df) == 0:
            logger.warning("No hierarchical relations found - skipping.")
            return

        logger.info("Creating hierarchical relations...")
        occupation_uuids = self._prefetch_uuids("Occupation")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Hierarchical Relations", unit="rel"):
            try:
                broader_uuid = record["broaderUri"].split("/")[-1]
                narrower_uuid = record["narrowerUri"].split("/")[-1]
                if broader_uuid not in occupation_uuids or narrower_uuid not in occupation_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Occupation", "from_uuid": narrower_uuid,
                    "ref_property": "broaderOccupation",
                    "to_class": "Occupation", "to_uuid": broader_uuid,
                })
            except Exception as e:
                logger.error(f"Failed to prepare hierarchical relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} hierarchical references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Hierarchical relations completed")

    def create_isco_group_relations(self) -> None:
        """Create relations between occupations and ISCO groups."""
        logger.info("Creating ISCO group relations...")
        try:
            isco_groups = self.client.get_objects(class_name="ISCOGroup")
            isco_by_code = {}
            for g in isco_groups:
                code = g.get("code")
                if code:
                    isco_by_code[code] = g["_id"]

            occupations = self.client.get_objects(class_name="Occupation")

            refs_batch = []
            for occ in tqdm(occupations, desc="ISCO Group Relations", unit="occ"):
                isco_code = occ.get("iscoCode")
                if not isco_code or isco_code not in isco_by_code:
                    continue
                refs_batch.append({
                    "from_class": "Occupation", "from_uuid": occ["_id"],
                    "ref_property": "memberOfISCOGroup",
                    "to_class": "ISCOGroup", "to_uuid": isco_by_code[isco_code],
                })

            if refs_batch:
                logger.info(f"Batch-inserting {len(refs_batch)} ISCO group references")
                self.client.batch_add_references(refs_batch)
            logger.info("ISCO group relations completed")
        except Exception as e:
            logger.error(f"Error creating ISCO group relations: {e}")

    def create_skill_collection_relations(self) -> None:
        """Create relations between skills and skill collections."""
        df = self.data_reader.read_csv("skillSkillRelations_en.csv")
        if df is None or len(df) == 0:
            logger.warning("No skill collection relations found - skipping.")
            return

        df = ESCODataReader.standardize_collection_relation_columns(df)
        if "conceptSchemeUri" not in df.columns or "skillUri" not in df.columns:
            logger.warning("Required columns not found in skill collection relations - skipping.")
            return

        logger.info("Creating skill collection relations...")
        collection_uuids = self._prefetch_uuids("SkillCollection")
        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Skill Collection Relations", unit="rel"):
            try:
                coll_uuid = record["conceptSchemeUri"].split("/")[-1]
                skill_uuid = record["skillUri"].split("/")[-1]
                if coll_uuid not in collection_uuids or skill_uuid not in skill_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Skill", "from_uuid": skill_uuid,
                    "ref_property": "memberOfSkillCollection",
                    "to_class": "SkillCollection", "to_uuid": coll_uuid,
                })
            except Exception as e:
                logger.error(f"Failed to prepare skill collection relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} skill-collection references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Skill collection relations completed")

    def create_skill_skill_relations(self) -> None:
        """Create skill-to-skill relations."""
        df = self.data_reader.read_csv("skillSkillRelations_en.csv")
        if df is None or len(df) == 0:
            logger.warning("No skill-skill relations found - skipping.")
            return

        logger.info("Creating skill-skill relations...")
        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Skill-Skill Relations", unit="rel"):
            try:
                skill_uuid = record["skillUri"].split("/")[-1]
                related_uuid = record["relatedSkillUri"].split("/")[-1]
                if skill_uuid not in skill_uuids or related_uuid not in skill_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Skill", "from_uuid": skill_uuid,
                    "ref_property": "hasRelatedSkill",
                    "to_class": "Skill", "to_uuid": related_uuid,
                })
            except Exception as e:
                logger.error(f"Failed to prepare skill-skill relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} skill-skill references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Skill-skill relations completed")

    def create_broader_skill_relations(self) -> None:
        """Create broader skill relations."""
        df = self.data_reader.read_csv("broaderRelationsSkillPillar_en.csv")
        if df is None:
            return

        df = ESCODataReader.standardize_hierarchy_columns(df)
        if "broaderUri" not in df.columns or "conceptUri" not in df.columns:
            logger.warning("Required columns not found in broader skill relations - skipping.")
            return
        if len(df) == 0:
            logger.warning("No broader skill relations found - skipping.")
            return

        logger.info("Creating broader skill relations...")
        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Broader Skill Relations", unit="rel"):
            try:
                skill_uuid = record["conceptUri"].split("/")[-1]
                broader_uuid = record["broaderUri"].split("/")[-1]
                if skill_uuid not in skill_uuids or broader_uuid not in skill_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Skill", "from_uuid": skill_uuid,
                    "ref_property": "broaderSkill",
                    "to_class": "Skill", "to_uuid": broader_uuid,
                })
            except Exception as e:
                logger.error(f"Failed to prepare broader skill relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} broader-skill references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Broader skill relations completed")
