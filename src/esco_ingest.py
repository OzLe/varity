import os
import pandas as pd
from tqdm import tqdm
import argparse
import yaml
from abc import ABC, abstractmethod
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

# Local imports
from src.infrastructure.database.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.external.embedding_utils import ESCOEmbedding
from src.shared.logging.structured_logger import configure_logging
from src.weaviate_semantic_search import VaritySemanticSearch

# ESCO v1.2.0 (English) – CSV classification import for Weaviate
# Oz Levi
# 2025-05-11

# Setup logging
logger = configure_logging()

class BaseIngestor(ABC):
    """Base class for ESCO data ingestion"""
    
    def __init__(self, config_path=None, profile='default'):
        """
        Initialize base ingestor
        
        Args:
            config_path (str): Path to YAML config file
            profile (str): Configuration profile to use
        """
        self.config = self._load_config(config_path, profile)
        self.esco_dir = self.config['app']['data_dir']
        self.batch_size = self.config['weaviate'].get('batch_size', 100)
        logger.info(f"Using batch size of {self.batch_size} for {profile} profile")

    def _load_config(self, config_path, profile):
        """Load configuration from YAML file"""
        if not config_path:
            config_path = self._get_default_config_path()
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config[profile]

    @abstractmethod
    def _get_default_config_path(self):
        """Get default configuration file path"""
        pass

    @abstractmethod
    def close(self):
        """Close database connection"""
        pass

    @abstractmethod
    def delete_all_data(self):
        """Delete all data from the database"""
        pass

    def process_csv_in_batches(self, file_path, process_func, heartbeat_callback=None):
        """
        Process a CSV file in batches with optional heartbeat updates.
        
        Args:
            file_path: Path to the CSV file
            process_func: Function to process each batch
            heartbeat_callback: Optional callback function for heartbeat updates
        """
        df = pd.read_csv(file_path)
        total_rows = len(df)
        rows_processed = 0
        
        with tqdm(total=total_rows, desc=f"Processing {os.path.basename(file_path)}", unit="rows",
                 bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            for start_idx in range(0, total_rows, self.batch_size):
                end_idx = min(start_idx + self.batch_size, total_rows)
                batch = df.iloc[start_idx:end_idx]
                process_func(batch)
                rows_processed += len(batch)
                pbar.update(len(batch))
                
                # Send heartbeat every 1000 rows
                if heartbeat_callback and rows_processed % 1000 == 0:
                    heartbeat_callback(rows_processed, total_rows)

    @abstractmethod
    def run_simple_ingestion(self):
        """Run a simplified ingestion process without business logic"""
        pass

    @abstractmethod
    def run_embeddings_only(self):
        """Run only the embedding generation and indexing"""
        pass

class WeaviateIngestor(BaseIngestor):
    """
    Weaviate-specific implementation of ESCO data ingestion.

    .. deprecated::
        Use :class:`~src.infrastructure.ingestion.ingestion_orchestrator.IngestionOrchestrator`
        for new code. This class is kept as a facade for backwards compatibility.
    """

    def __init__(self, config_path: str = "config/weaviate_config.yaml", profile: str = "default", client: Optional[WeaviateClient] = None):
        """Initialize the Weaviate ingestor."""
        import warnings
        warnings.warn(
            "WeaviateIngestor is deprecated. Use IngestionOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(config_path, profile)
        self.client = client or WeaviateClient(url=os.getenv("WEAVIATE_URL", "http://weaviate:8080"))
        self.embedding_util = ESCOEmbedding()

    def _get_default_config_path(self):
        return 'config/weaviate_config.yaml'

    def initialize_schema(self):
        """Initialize the Weaviate schema if not already initialized."""
        try:
            if not self.client.is_connected():
                logger.info("Initializing Weaviate schema...")
                self.client.create_schema(self._get_schema())
                logger.info("Schema initialization completed")
            else:
                logger.info("Schema already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {str(e)}")
            raise

    def _get_schema(self) -> Dict[str, Any]:
        """Get the Weaviate schema definition."""
        return {
            "classes": [
                {
                    "class": "Skill",
                    "description": "A skill from the ESCO classification",
                    "vectorizer": "text2vec-transformers",
                    "properties": [
                        {
                            "name": "uri",
                            "dataType": ["string"],
                            "description": "URI of the skill"
                        },
                        {
                            "name": "preferredLabel",
                            "dataType": ["string"],
                            "description": "Preferred label of the skill"
                        },
                        {
                            "name": "description",
                            "dataType": ["text"],
                            "description": "Description of the skill"
                        }
                    ]
                },
                {
                    "class": "Occupation",
                    "description": "An occupation from the ESCO classification",
                    "vectorizer": "text2vec-transformers",
                    "properties": [
                        {
                            "name": "uri",
                            "dataType": ["string"],
                            "description": "URI of the occupation"
                        },
                        {
                            "name": "preferredLabel",
                            "dataType": ["string"],
                            "description": "Preferred label of the occupation"
                        },
                        {
                            "name": "description",
                            "dataType": ["text"],
                            "description": "Description of the occupation"
                        }
                    ]
                }
            ]
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _standardize_hierarchy_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename alternative hierarchy column names to the expected
        `broaderUri` / `narrowerUri`.

        Handles variants found in ESCO CSVs such as:
        - broaderConceptUri / narrowerConceptUri
        - parentUri / childUri
        - broaderSkillUri / skillUri   (skill hierarchy)
        - conceptUri / targetUri       (child/narrower)
        - Level X URI format           (skills hierarchy)
        """
        rename_map = {}
        
        # Handle Level X URI format
        if 'Level 0 URI' in df.columns:
            # For each row, find the highest non-empty Level URI
            def get_broader_narrower(row):
                levels = [f'Level {i} URI' for i in range(4)]  # ESCO uses up to Level 3
                non_empty_levels = [level for level in levels if level in df.columns and pd.notna(row[level]) and row[level] != '']
                if len(non_empty_levels) >= 2:
                    # The broader URI is the second-to-last non-empty level
                    broader = row[non_empty_levels[-2]]
                    # The narrower URI is the last non-empty level
                    narrower = row[non_empty_levels[-1]]
                    return pd.Series([broader, narrower])
                return pd.Series([None, None])
            
            # Apply the function to create broader/narrower columns
            df[['broaderUri', 'narrowerUri']] = df.apply(get_broader_narrower, axis=1)
            # Drop rows where we couldn't determine the relationship
            df = df.dropna(subset=['broaderUri', 'narrowerUri'])
            # Drop rows where broader and narrower are the same
            df = df[df['broaderUri'] != df['narrowerUri']]
            return df
            
        # Handle other formats
        if 'broaderUri' not in df.columns:
            if 'broaderConceptUri' in df.columns:
                rename_map['broaderConceptUri'] = 'broaderUri'
            elif 'parentUri' in df.columns:
                rename_map['parentUri'] = 'broaderUri'
            elif 'broaderSkillUri' in df.columns:
                rename_map['broaderSkillUri'] = 'broaderUri'

        if 'narrowerUri' not in df.columns:
            if 'narrowerConceptUri' in df.columns:
                rename_map['narrowerConceptUri'] = 'narrowerUri'
            elif 'childUri' in df.columns:
                rename_map['childUri'] = 'narrowerUri'
            elif 'conceptUri' in df.columns:
                rename_map['conceptUri'] = 'narrowerUri'
            elif 'targetUri' in df.columns:
                rename_map['targetUri'] = 'narrowerUri'
            elif 'skillUri' in df.columns:
                rename_map['skillUri'] = 'narrowerUri'

        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def _standardize_collection_relation_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename alternative column names for skill‑collection relation CSVs so the rest
        of the code can safely assume `conceptSchemeUri` and `skillUri`.

        Handles variants such as:
        - collectionUri / conceptScheme / schemeUri  → conceptSchemeUri
        - conceptUri / targetUri / skillID           → skillUri
        """
        rename_map = {}
        if 'conceptSchemeUri' not in df.columns:
            if 'collectionUri' in df.columns:
                rename_map['collectionUri'] = 'conceptSchemeUri'
            elif 'conceptScheme' in df.columns:
                rename_map['conceptScheme'] = 'conceptSchemeUri'
            elif 'schemeUri' in df.columns:
                rename_map['schemeUri'] = 'conceptSchemeUri'
        if 'skillUri' not in df.columns:
            if 'conceptUri' in df.columns:
                rename_map['conceptUri'] = 'skillUri'
            elif 'targetUri' in df.columns:
                rename_map['targetUri'] = 'skillUri'
            elif 'skillID' in df.columns:
                rename_map['skillID'] = 'skillUri'
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def close(self):
        """Close database connection"""
        if self.client:
            # Weaviate client doesn't need explicit closing
            pass

    def delete_all_data(self):
        """Delete all data from the database"""
        try:
            logger.info("Deleting all data from Weaviate...")
            
            # Delete schema which removes all data
            self.client.delete_schema()
            logger.info("All data deleted successfully")
            
            # Recreate schema
            self.client.ensure_schema()
            logger.info("Schema recreated")
            
        except Exception as e:
            logger.error(f"Failed to delete all data: {str(e)}")
            raise

    def check_class_exists(self, class_name: str) -> bool:
        """
        Check if a class exists and has data.
        
        Args:
            class_name: Name of the class to check
            
        Returns:
            bool: True if class exists and has data, False otherwise
        """
        try:
            repo = self.client.get_repository(class_name)
            count = repo.count_objects()
            return count > 0
        except Exception as e:
            logger.warning(f"Error checking if class {class_name} exists: {str(e)}")
            return False

    def ingest_isco_groups(self):
        """Ingest ISCO groups into Weaviate using batch insertion."""
        file_path = os.path.join(self.esco_dir, "ISCOGroups_en.csv")
        if not os.path.exists(file_path):
            logger.warning(f"ISCO groups file not found: {file_path} – skipping.")
            return

        logger.info(f"Ingesting ISCO groups from {file_path}")

        def process_batch(batch):
            objects = []
            uuids = []
            for record in batch.to_dict("records"):
                try:
                    isco_group_data = {
                        "uri": record["conceptUri"],
                        "code": record.get("code", ""),
                        "preferredLabel_en": record.get("preferredLabel", ""),
                        "description_en": record.get("description", ""),
                        "iscoLevel": record.get("iscoLevel", ""),
                    }
                    isco_group_data = {k: v for k, v in isco_group_data.items() if v is not None and v != ""}
                    uuid = isco_group_data["uri"].split("/")[-1]
                    objects.append(isco_group_data)
                    uuids.append(uuid)
                except Exception as e:
                    logger.error(f"Failed to prepare ISCO group {record.get('conceptUri', 'unknown')}: {e}")
            if objects:
                self.client.batch_add_objects("ISCOGroup", objects, uuids)

        self.process_csv_in_batches(file_path, process_batch)
        logger.info("ISCO group ingestion completed")

    def ingest_occupations(self):
        """Ingest occupations from CSV file using batch insertion."""
        logger.info("Starting occupation ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    occupation = {
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "definition_en": record.get("definition_en", ""),
                        "code": record.get("code", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else []
                    }
                    objects.append(occupation)
                except Exception as e:
                    logger.error(f"Error preparing occupation {record.get('conceptUri', 'unknown')}: {e}")
            if objects:
                self.client.batch_add_objects("Occupation", objects)

        def update_heartbeat(processed, total):
            self.client.set_ingestion_metadata(
                status="in_progress",
                details={
                    "step": "ingest_occupations",
                    "progress": f"{processed}/{total}",
                    "last_heartbeat": datetime.utcnow().isoformat()
                }
            )

        occupations_file = os.path.join(self.esco_dir, "occupations_en.csv")
        self.process_csv_in_batches(occupations_file, process_batch, update_heartbeat)
        logger.info("Occupation ingestion completed")

    def ingest_skills(self):
        """Ingest skills from CSV file using batch insertion."""
        logger.info("Starting skill ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    skill = {
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "skillType": record.get("skillType", ""),
                        "reuseLevel": record.get("reuseLevel", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else []
                    }
                    objects.append(skill)
                except Exception as e:
                    logger.error(f"Error preparing skill {record.get('conceptUri', 'unknown')}: {e}")
            if objects:
                self.client.batch_add_objects("Skill", objects)

        def update_heartbeat(processed, total):
            self.client.set_ingestion_metadata(
                status="in_progress",
                details={
                    "step": "ingest_skills",
                    "progress": f"{processed}/{total}",
                    "last_heartbeat": datetime.utcnow().isoformat()
                }
            )

        skills_file = os.path.join(self.esco_dir, "skills_en.csv")
        self.process_csv_in_batches(skills_file, process_batch, update_heartbeat)
        logger.info("Skill ingestion completed")

    def _prefetch_uuids(self, class_name: str) -> set:
        """Pre-fetch all UUIDs for a class into a set for fast in-memory lookups."""
        logger.info(f"Pre-fetching UUIDs for {class_name}...")
        uuids = set(self.client.get_all_uuids(class_name))
        logger.info(f"Pre-fetched {len(uuids)} UUIDs for {class_name}")
        return uuids

    def create_skill_relations(self):
        """Create occupation-skill relations using batch references and pre-fetched UUIDs."""
        file_path = os.path.join(self.esco_dir, "occupationSkillRelations_en.csv")
        if not os.path.exists(file_path):
            logger.warning(f"Occupation-skill relations file not found: {file_path} – skipping.")
            return

        logger.info(f"Creating occupation-skill relations from {file_path}")

        occupation_uuids = self._prefetch_uuids("Occupation")
        skill_uuids = self._prefetch_uuids("Skill")

        df = pd.read_csv(file_path)
        if len(df) == 0:
            logger.warning("No occupation-skill relations found – skipping.")
            return

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Preparing Occupation-Skill Relations", unit="rel"):
            try:
                occupation_uuid = record['occupationUri'].split('/')[-1]
                skill_uuid = record['skillUri'].split('/')[-1]
                relation_type = record.get('relationType', 'related')

                if occupation_uuid not in occupation_uuids or skill_uuid not in skill_uuids:
                    skipped += 1
                    continue

                ref_prop = "hasEssentialSkill" if relation_type == "essential" else (
                    "hasOptionalSkill" if relation_type == "optional" else "hasEssentialSkill"
                )
                refs_batch.append({
                    "from_class": "Occupation", "from_uuid": occupation_uuid,
                    "ref_property": ref_prop,
                    "to_class": "Skill", "to_uuid": skill_uuid
                })
            except Exception as e:
                logger.error(f"Failed to prepare occupation-skill relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} occupation-skill references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Occupation-skill relations completed")

    def create_hierarchical_relations(self):
        """Create hierarchical relations between occupations using batch references."""
        file_path = os.path.join(self.esco_dir, "broaderRelationsOccPillar_en.csv")
        if not os.path.exists(file_path):
            logger.warning(f"Hierarchical relations file not found: {file_path} – skipping.")
            return

        logger.info(f"Creating hierarchical relations from {file_path}")

        df = pd.read_csv(file_path)
        df = self._standardize_hierarchy_columns(df)

        if 'broaderUri' not in df.columns or 'narrowerUri' not in df.columns:
            logger.warning("Required columns 'broaderUri' and 'narrowerUri' not found – skipping.")
            return
        if len(df) == 0:
            logger.warning("No hierarchical relations found – skipping.")
            return

        occupation_uuids = self._prefetch_uuids("Occupation")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Preparing Hierarchical Relations", unit="rel"):
            try:
                broader_uuid = record['broaderUri'].split('/')[-1]
                narrower_uuid = record['narrowerUri'].split('/')[-1]
                if broader_uuid not in occupation_uuids or narrower_uuid not in occupation_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Occupation", "from_uuid": narrower_uuid,
                    "ref_property": "broaderOccupation",
                    "to_class": "Occupation", "to_uuid": broader_uuid
                })
            except Exception as e:
                logger.error(f"Failed to prepare hierarchical relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} hierarchical references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Hierarchical relations completed")

    def create_isco_group_relations(self):
        """Create relations between occupations and ISCO groups using pre-loaded dict."""
        logger.info("Creating ISCO group relations...")

        try:
            # Pre-load ISCO groups keyed by code
            isco_groups = self.client.get_objects(class_name="ISCOGroup")
            isco_by_code = {}
            for g in isco_groups:
                code = g.get("code")
                if code:
                    isco_by_code[code] = g["_id"]

            occupations = self.client.get_objects(class_name="Occupation")

            refs_batch = []
            for occupation in tqdm(occupations, desc="Preparing ISCO Group Relations", unit="occ"):
                isco_code = occupation.get("iscoCode")
                if not isco_code or isco_code not in isco_by_code:
                    continue
                refs_batch.append({
                    "from_class": "Occupation", "from_uuid": occupation["_id"],
                    "ref_property": "memberOfISCOGroup",
                    "to_class": "ISCOGroup", "to_uuid": isco_by_code[isco_code]
                })

            if refs_batch:
                logger.info(f"Batch-inserting {len(refs_batch)} ISCO group references")
                self.client.batch_add_references(refs_batch)
            logger.info("ISCO group relations completed")

        except Exception as e:
            logger.error(f"Error creating ISCO group relations: {e}")

    def ingest_skill_groups(self):
        """Ingest skill groups from CSV file using batch insertion."""
        logger.info("Starting skill group ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    skill_group = {
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else []
                    }
                    objects.append(skill_group)
                except Exception as e:
                    logger.error(f"Error preparing skill group {record.get('conceptUri', 'unknown')}: {e}")
            if objects:
                self.client.batch_add_objects("SkillGroup", objects)

        def update_heartbeat(processed, total):
            self.client.set_ingestion_metadata(
                status="in_progress",
                details={
                    "step": "ingest_skill_groups",
                    "progress": f"{processed}/{total}",
                    "last_heartbeat": datetime.utcnow().isoformat()
                }
            )

        skill_groups_file = os.path.join(self.esco_dir, "skillGroups_en.csv")
        self.process_csv_in_batches(skill_groups_file, process_batch, update_heartbeat)
        logger.info("Skill group ingestion completed")

    def ingest_skill_collections(self):
        """Ingest skill collections from CSV file using batch insertion."""
        logger.info("Starting skill collection ingestion...")

        def process_batch(batch):
            objects = []
            for record in batch.to_dict("records"):
                try:
                    alt = record.get("altLabels_en", "")
                    collection = {
                        "uri": record["conceptUri"],
                        "preferredLabel_en": record["preferredLabel_en"],
                        "description_en": record.get("description_en", ""),
                        "altLabels_en": alt.split("|") if isinstance(alt, str) and alt else []
                    }
                    objects.append(collection)
                except Exception as e:
                    logger.error(f"Error preparing skill collection {record.get('conceptUri', 'unknown')}: {e}")
            if objects:
                self.client.batch_add_objects("SkillCollection", objects)

        def update_heartbeat(processed, total):
            self.client.set_ingestion_metadata(
                status="in_progress",
                details={
                    "step": "ingest_skill_collections",
                    "progress": f"{processed}/{total}",
                    "last_heartbeat": datetime.utcnow().isoformat()
                }
            )

        collections_file = os.path.join(self.esco_dir, "conceptSchemes_en.csv")
        self.process_csv_in_batches(collections_file, process_batch, update_heartbeat)
        logger.info("Skill collection ingestion completed")

    def create_skill_collection_relations(self):
        """Create relations between skills and skill collections using batch references."""
        file_path = os.path.join(self.esco_dir, "skillSkillRelations_en.csv")
        if not os.path.exists(file_path):
            logger.warning(f"Skill collection relations file not found: {file_path} – skipping.")
            return

        logger.info(f"Creating skill collection relations from {file_path}")

        df = pd.read_csv(file_path)
        df = self._standardize_collection_relation_columns(df)

        if 'conceptSchemeUri' not in df.columns or 'skillUri' not in df.columns:
            logger.warning("Required columns not found in skill collection relations file – skipping.")
            return
        if len(df) == 0:
            logger.warning("No skill collection relations found – skipping.")
            return

        collection_uuids = self._prefetch_uuids("SkillCollection")
        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Preparing Skill Collection Relations", unit="rel"):
            try:
                collection_uuid = record['conceptSchemeUri'].split('/')[-1]
                skill_uuid = record['skillUri'].split('/')[-1]
                if collection_uuid not in collection_uuids or skill_uuid not in skill_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Skill", "from_uuid": skill_uuid,
                    "ref_property": "memberOfSkillCollection",
                    "to_class": "SkillCollection", "to_uuid": collection_uuid
                })
            except Exception as e:
                logger.error(f"Failed to prepare skill collection relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} skill-collection references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Skill collection relations completed")

    def create_skill_skill_relations(self):
        """Create skill-to-skill relations using batch references."""
        file_path = os.path.join(self.esco_dir, "skillSkillRelations_en.csv")
        if not os.path.exists(file_path):
            logger.warning(f"Skill-skill relations file not found: {file_path} – skipping.")
            return

        logger.info(f"Creating skill-skill relations from {file_path}")

        df = pd.read_csv(file_path)
        if len(df) == 0:
            logger.warning("No skill-skill relations found – skipping.")
            return

        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Preparing Skill-Skill Relations", unit="rel"):
            try:
                skill_uuid = record['skillUri'].split('/')[-1]
                related_uuid = record['relatedSkillUri'].split('/')[-1]
                if skill_uuid not in skill_uuids or related_uuid not in skill_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Skill", "from_uuid": skill_uuid,
                    "ref_property": "hasRelatedSkill",
                    "to_class": "Skill", "to_uuid": related_uuid
                })
            except Exception as e:
                logger.error(f"Failed to prepare skill-skill relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} skill-skill references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Skill-skill relations completed")

    def create_broader_skill_relations(self):
        """Create broader skill relations using batch references."""
        file_path = os.path.join(self.esco_dir, "broaderRelationsSkillPillar_en.csv")
        if not os.path.exists(file_path):
            logger.warning(f"Broader skill relations file not found: {file_path} – skipping.")
            return

        logger.info(f"Creating broader skill relations from {file_path}")

        df = pd.read_csv(file_path)
        df = self._standardize_hierarchy_columns(df)

        if 'broaderUri' not in df.columns or 'conceptUri' not in df.columns:
            logger.warning("Required columns not found in broader skill relations file – skipping.")
            return
        if len(df) == 0:
            logger.warning("No valid relations found in broader relations file – skipping.")
            return

        skill_uuids = self._prefetch_uuids("Skill")

        refs_batch = []
        skipped = 0
        for record in tqdm(df.to_dict("records"), desc="Preparing Broader Skill Relations", unit="rel"):
            try:
                skill_uuid = record['conceptUri'].split('/')[-1]
                broader_uuid = record['broaderUri'].split('/')[-1]
                if skill_uuid not in skill_uuids or broader_uuid not in skill_uuids:
                    skipped += 1
                    continue
                refs_batch.append({
                    "from_class": "Skill", "from_uuid": skill_uuid,
                    "ref_property": "broaderSkill",
                    "to_class": "Skill", "to_uuid": broader_uuid
                })
            except Exception as e:
                logger.error(f"Failed to prepare broader skill relation: {e}")

        if refs_batch:
            logger.info(f"Batch-inserting {len(refs_batch)} broader-skill references (skipped {skipped})")
            self.client.batch_add_references(refs_batch)
        logger.info("Broader skill relations completed")

    def run_simple_ingestion(self):
        """
        Run a simplified ingestion process for all entities and relationships.

        Delegates to IngestionOrchestrator when available, falls back to
        the legacy inline implementation.
        """
        try:
            from src.infrastructure.ingestion.ingestion_orchestrator import IngestionOrchestrator
            logger.info("Delegating to IngestionOrchestrator")
            orchestrator = IngestionOrchestrator(
                client=self.client,
                data_dir=self.esco_dir,
                batch_size=self.batch_size,
            )
            orchestrator.run_complete_ingestion()
            return
        except ImportError:
            logger.info("IngestionOrchestrator not available, using legacy path")

        try:
            logger.info("Starting simple ingestion process (legacy)")

            # Initialize schema
            self.initialize_schema()

            # Ingest all entities
            self.ingest_isco_groups()
            self.ingest_occupations()
            self.ingest_skills()
            self.ingest_skill_groups()
            self.ingest_skill_collections()

            # Create all relationships
            self.create_skill_relations()
            self.create_hierarchical_relations()
            self.create_isco_group_relations()
            self.create_skill_collection_relations()
            self.create_skill_skill_relations()
            self.create_broader_skill_relations()

            logger.info("Simple ingestion process completed")

        except Exception as e:
            logger.error(f"Simple ingestion process failed: {str(e)}")
            raise

    def run_embeddings_only(self):
        """Run only the Weaviate embedding generation and indexing"""
        try:
            # Weaviate handles embeddings during ingestion
            logger.info("Weaviate embeddings are generated during ingestion")
        except Exception as e:
            logger.error(f"Error during Weaviate embedding generation: {str(e)}")
            raise

def create_ingestor(config_path=None, profile='default'):
    """
    Factory function to create the Weaviate ingestor
    
    Args:
        config_path (str): Path to configuration file
        profile (str): Configuration profile to use
        
    Returns:
        WeaviateIngestor: Weaviate ingestor instance
    """
    return WeaviateIngestor(config_path, profile)

def main():
    parser = argparse.ArgumentParser(description='ESCO Data Ingestion Tool for Weaviate')
    
    # Configuration parameters
    parser.add_argument('--config', type=str,
                      help='Path to YAML config file')
    parser.add_argument('--profile', type=str, default='default',
                      help='Configuration profile to use')
    
    # Execution mode
    parser.add_argument('--embeddings-only', action='store_true',
                      help='Run only the embedding generation and indexing')
    
    args = parser.parse_args()
    
    # Create ingestor instance
    ingestor = create_ingestor(args.config, args.profile)
    
    try:
        # Run appropriate process
        if args.embeddings_only:
            ingestor.run_embeddings_only()
        else:
            # Use simple ingestion instead of the business logic heavy run_ingest
            ingestor.run_simple_ingestion()
    finally:
        ingestor.close()

if __name__ == "__main__":
    main()