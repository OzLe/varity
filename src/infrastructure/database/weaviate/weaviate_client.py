"""
Weaviate client for database operations.

This module provides a client for interacting with Weaviate,
handling connections and basic operations.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

import yaml
import weaviate
from weaviate import Client
from weaviate.util import generate_uuid5

from ....core.interfaces import ClientInterface
from ....core.entities import (
    Document,
    SearchQuery,
    SearchResult
)

logger = logging.getLogger(__name__)


class _RepositoryProxy:
    """Lightweight repository wrapper returned by get_repository()."""

    def __init__(self, client: Client, class_name: str):
        self._client = client
        self._class_name = class_name

    def count_objects(self) -> int:
        """Return the total number of objects in the class."""
        result = (
            self._client.query
            .aggregate(self._class_name)
            .with_meta_count()
            .do()
        )
        return result["data"]["Aggregate"][self._class_name][0]["meta"]["count"]


class WeaviateClient(ClientInterface):
    """
    Client for Weaviate database operations.

    Provides both the async methods required by ClientInterface and
    synchronous convenience methods used by legacy modules
    (esco_ingest.py, weaviate_semantic_search.py).
    """

    def __init__(
        self,
        url: str,
        auth_client_secret: Optional[weaviate.AuthApiKey] = None,
        timeout_config: Optional[tuple] = None,
        additional_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the client.

        Args:
            url: Weaviate instance URL
            auth_client_secret: Optional authentication credentials
            timeout_config: Optional timeout configuration
            additional_headers: Optional additional headers
        """
        self.client = Client(
            url=url,
            auth_client_secret=auth_client_secret,
            timeout_config=timeout_config or (5, 60),
            additional_headers=additional_headers
        )

    # ------------------------------------------------------------------ #
    # Connection helpers
    # ------------------------------------------------------------------ #

    def is_connected(self) -> bool:
        """Check if the client is connected to Weaviate."""
        try:
            self.client.schema.get()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Synchronous methods used by legacy modules
    # ------------------------------------------------------------------ #

    def add_object(
        self,
        class_name: str,
        properties: Dict[str, Any],
        uuid: Optional[str] = None
    ) -> str:
        """Insert a single object into Weaviate."""
        return self.client.data_object.create(
            class_name=class_name,
            data_object=properties,
            uuid=uuid
        )

    def batch_add_objects(
        self,
        class_name: str,
        objects: List[Dict[str, Any]],
        uuids: Optional[List[Optional[str]]] = None
    ) -> None:
        """Insert multiple objects in a single Weaviate batch call."""
        with self.client.batch as batch:
            batch.batch_size = 100
            for idx, props in enumerate(objects):
                uid = uuids[idx] if uuids and idx < len(uuids) else None
                batch.add_data_object(
                    class_name=class_name,
                    data_object=props,
                    uuid=uid
                )

    def batch_add_references(
        self,
        references: List[Dict[str, str]]
    ) -> None:
        """
        Add multiple cross-references in a single batch call.

        Each entry in *references* must be a dict with keys:
        from_class, from_uuid, ref_property, to_class, to_uuid.
        """
        with self.client.batch as batch:
            batch.batch_size = 100
            for ref in references:
                batch.add_reference(
                    from_object_class_name=ref["from_class"],
                    from_object_uuid=ref["from_uuid"],
                    from_property_name=ref["ref_property"],
                    to_object_class_name=ref["to_class"],
                    to_object_uuid=ref["to_uuid"]
                )

    def check_object_exists(self, class_name: str, uuid: str) -> bool:
        """Check whether an object with the given UUID exists."""
        try:
            obj = self.client.data_object.get_by_id(uuid, class_name=class_name)
            return obj is not None
        except Exception:
            return False

    def get_objects(
        self,
        class_name: str,
        property: Optional[str] = None,
        value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve objects via GraphQL, optionally filtered by a property value.

        Each returned dict includes an ``_id`` key with the object UUID.
        """
        # Determine which properties to fetch
        schema = self.client.schema.get(class_name)
        prop_names = [p["name"] for p in schema.get("properties", [])]

        query = (
            self.client.query
            .get(class_name, prop_names)
            .with_additional(["id"])
        )

        if property and value:
            query = query.with_where({
                "path": [property],
                "operator": "Equal",
                "valueString": value
            })

        query = query.with_limit(10000)
        result = query.do()

        objects = result.get("data", {}).get("Get", {}).get(class_name, [])
        # Flatten _additional.id into _id for convenience
        for obj in objects:
            additional = obj.pop("_additional", {})
            obj["_id"] = additional.get("id")
        return objects

    def get_all_uuids(self, class_name: str) -> List[str]:
        """Fetch all UUIDs for a class using cursor-based pagination."""
        uuids: List[str] = []
        cursor = None
        batch_size = 500

        while True:
            query = (
                self.client.query
                .get(class_name)
                .with_additional(["id"])
                .with_limit(batch_size)
            )
            if cursor:
                query = query.with_after(cursor)

            result = query.do()
            objects = result.get("data", {}).get("Get", {}).get(class_name, [])
            if not objects:
                break

            for obj in objects:
                uid = obj.get("_additional", {}).get("id")
                if uid:
                    uuids.append(uid)
                    cursor = uid

            if len(objects) < batch_size:
                break

        return uuids

    # ------------------------------------------------------------------ #
    # Metadata / ingestion status
    # ------------------------------------------------------------------ #

    _METADATA_UUID = "00000000-0000-0000-0000-000000000001"

    def set_ingestion_metadata(self, status: str, details: Any = None) -> None:
        """Create or update the singleton Metadata object tracking ingestion."""
        props = {
            "metaType": "ingestion_status",
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "details": json.dumps(details) if details else ""
        }
        try:
            existing = self.client.data_object.get_by_id(
                self._METADATA_UUID, class_name="Metadata"
            )
            if existing:
                self.client.data_object.update(
                    class_name="Metadata",
                    uuid=self._METADATA_UUID,
                    data_object=props
                )
            else:
                self.client.data_object.create(
                    class_name="Metadata",
                    data_object=props,
                    uuid=self._METADATA_UUID
                )
        except Exception:
            # Object doesn't exist yet — create it
            try:
                self.client.data_object.create(
                    class_name="Metadata",
                    data_object=props,
                    uuid=self._METADATA_UUID
                )
            except Exception as e:
                logger.warning(f"Failed to set ingestion metadata: {e}")

    def get_ingestion_status(self) -> Dict[str, Any]:
        """Read ingestion status from the Metadata class."""
        try:
            obj = self.client.data_object.get_by_id(
                self._METADATA_UUID, class_name="Metadata"
            )
            if obj and "properties" in obj:
                props = obj["properties"]
                details = props.get("details", "")
                if isinstance(details, str) and details:
                    try:
                        details = json.loads(details)
                    except json.JSONDecodeError:
                        pass
                return {
                    "status": props.get("status", "unknown"),
                    "timestamp": props.get("timestamp"),
                    "details": details
                }
        except Exception as e:
            logger.debug(f"Could not read ingestion status: {e}")
        return {"status": "unknown", "timestamp": None, "details": {}}

    # ------------------------------------------------------------------ #
    # Schema management
    # ------------------------------------------------------------------ #

    def ensure_schema(self) -> None:
        """Create the full ESCO schema from resources/schemas/*.yaml if missing."""
        existing = self.client.schema.get()
        existing_names = {c["class"] for c in existing.get("classes", [])}

        schemas_dir = self._find_schemas_dir()
        if not schemas_dir:
            logger.warning("Could not locate resources/schemas directory")
            return

        # Load reference definitions
        refs_path = os.path.join(schemas_dir, "references.yaml")
        references: Dict[str, List[Dict]] = {}
        if os.path.exists(refs_path):
            with open(refs_path, "r") as f:
                references = yaml.safe_load(f) or {}

        # Load and create each class schema
        schema_files = [
            "metadata.yaml",
            "isco_group.yaml",
            "occupation.yaml",
            "skill.yaml",
            "skill_collection.yaml",
            "skill_group.yaml",
        ]

        for fname in schema_files:
            fpath = os.path.join(schemas_dir, fname)
            if not os.path.exists(fpath):
                continue

            with open(fpath, "r") as f:
                schema_def = yaml.safe_load(f)

            class_name = schema_def["class"]
            if class_name in existing_names:
                continue

            # Build Weaviate class definition
            class_obj: Dict[str, Any] = {
                "class": class_name,
                "vectorizer": schema_def.get("vectorizer", "none"),
                "properties": [],
            }

            # Add properties
            for prop in schema_def.get("properties", []):
                p: Dict[str, Any] = {
                    "name": prop["name"],
                    "dataType": prop["dataType"],
                }
                if "tokenization" in prop:
                    p["tokenization"] = prop["tokenization"]
                class_obj["properties"].append(p)

            # Add cross-reference properties from references.yaml
            if class_name in references:
                for ref in references[class_name]:
                    class_obj["properties"].append({
                        "name": ref["name"],
                        "dataType": ref["dataType"],
                    })

            try:
                self.client.schema.create_class(class_obj)
                logger.info(f"Created schema class: {class_name}")
                existing_names.add(class_name)
            except Exception as e:
                logger.warning(f"Failed to create class {class_name}: {e}")

    def delete_schema(self) -> None:
        """Delete all schema classes (synchronous)."""
        self.client.schema.delete_all()

    @staticmethod
    def _find_schemas_dir() -> Optional[str]:
        """Locate the resources/schemas directory."""
        candidates = [
            os.path.join(os.getcwd(), "resources", "schemas"),
            os.path.join("/app", "resources", "schemas"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "resources", "schemas"),
        ]
        for candidate in candidates:
            normalized = os.path.normpath(candidate)
            if os.path.isdir(normalized):
                return normalized
        return None

    # ------------------------------------------------------------------ #
    # Repository proxy
    # ------------------------------------------------------------------ #

    def get_repository(self, class_name: str) -> _RepositoryProxy:
        """Return a lightweight repository wrapper for the given class."""
        return _RepositoryProxy(self.client, class_name)

    # ------------------------------------------------------------------ #
    # Cross-reference (relation) methods
    # ------------------------------------------------------------------ #

    def _add_reference(
        self,
        from_class: str,
        from_uuid: str,
        ref_property: str,
        to_class: str,
        to_uuid: str
    ) -> None:
        """Add a cross-reference between two objects."""
        self.client.data_object.reference.add(
            from_class_name=from_class,
            from_uuid=from_uuid,
            from_property_name=ref_property,
            to_class_name=to_class,
            to_uuid=to_uuid
        )

    def add_essential_skill_relation(
        self, class_name: str, uuid: str, skill_uuid: str
    ) -> None:
        """Occupation -> hasEssentialSkill -> Skill."""
        self._add_reference(class_name, uuid, "hasEssentialSkill", "Skill", skill_uuid)

    def add_optional_skill_relation(
        self, class_name: str, uuid: str, skill_uuid: str
    ) -> None:
        """Occupation -> hasOptionalSkill -> Skill."""
        self._add_reference(class_name, uuid, "hasOptionalSkill", "Skill", skill_uuid)

    def add_broader_occupation_relation(
        self, class_name: str, uuid: str, broader_uuid: str
    ) -> None:
        """Occupation -> broaderOccupation -> Occupation."""
        self._add_reference(class_name, uuid, "broaderOccupation", "Occupation", broader_uuid)

    def add_isco_group_relation(
        self, class_name: str, uuid: str, isco_group_uuid: str
    ) -> None:
        """Occupation -> memberOfISCOGroup -> ISCOGroup."""
        self._add_reference(class_name, uuid, "memberOfISCOGroup", "ISCOGroup", isco_group_uuid)

    def add_skill_collection_relation(
        self, class_name: str, uuid: str, collection_uuid: str
    ) -> None:
        """Skill -> memberOfSkillCollection -> SkillCollection."""
        self._add_reference(class_name, uuid, "memberOfSkillCollection", "SkillCollection", collection_uuid)

    def add_related_skill_relation(
        self, class_name: str, uuid: str, related_uuid: str,
        relation_type: str = "related"
    ) -> None:
        """Skill -> hasRelatedSkill -> Skill."""
        self._add_reference(class_name, uuid, "hasRelatedSkill", "Skill", related_uuid)

    def add_broader_skill_relation(
        self, class_name: str, uuid: str, broader_uuid: str
    ) -> None:
        """Skill -> broaderSkill -> Skill."""
        self._add_reference(class_name, uuid, "broaderSkill", "Skill", broader_uuid)

    # ------------------------------------------------------------------ #
    # Async methods (ClientInterface)
    # ------------------------------------------------------------------ #

    async def create_schema(self, schema: Dict[str, Any]) -> None:
        """Create database schema."""
        self.client.schema.create(schema)

    async def create_object(
        self,
        class_name: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None
    ) -> str:
        """Create a new object (async interface)."""
        return self.client.data_object.create(
            class_name=class_name,
            data_object=properties,
            vector=vector
        )

    async def get_object(
        self,
        class_name: str,
        object_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get an object by ID (async interface)."""
        try:
            return self.client.data_object.get_by_id(
                class_name=class_name,
                uuid=object_id
            )
        except Exception:
            return None

    async def update_object(
        self,
        class_name: str,
        object_id: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None
    ) -> None:
        """Update an object (async interface)."""
        self.client.data_object.update(
            class_name=class_name,
            uuid=object_id,
            data_object=properties,
            vector=vector
        )

    async def delete_object(
        self,
        class_name: str,
        object_id: str
    ) -> None:
        """Delete an object (async interface)."""
        self.client.data_object.delete(
            class_name=class_name,
            uuid=object_id
        )

    async def search(
        self,
        query: SearchQuery
    ) -> List[Dict[str, Any]]:
        """Search for objects (async interface)."""
        weaviate_query = (
            self.client.query
            .get(query.class_name)
            .with_additional(["vector", "distance"])
        )

        if query.text:
            weaviate_query = weaviate_query.with_near_text({
                "concepts": [query.text]
            })

        if query.vector:
            weaviate_query = weaviate_query.with_near_vector({
                "vector": query.vector
            })

        if query.filters:
            weaviate_query = weaviate_query.with_where(query.filters)

        weaviate_query = (
            weaviate_query
            .with_limit(query.limit)
            .with_offset(query.offset)
        )

        result = weaviate_query.do()
        return result["data"]["Get"][query.class_name]

    async def batch_create(
        self,
        class_name: str,
        objects: List[Dict[str, Any]]
    ) -> List[str]:
        """Create multiple objects in batch (async interface)."""
        with self.client.batch as batch:
            batch.batch_size = 100
            object_ids = []

            for obj in objects:
                object_id = generate_uuid5(obj)
                batch.add_data_object(
                    class_name=class_name,
                    data_object=obj,
                    uuid=object_id
                )
                object_ids.append(object_id)

            return object_ids

    async def batch_delete(
        self,
        class_name: str,
        object_ids: List[str]
    ) -> None:
        """Delete multiple objects in batch (async interface)."""
        with self.client.batch as batch:
            batch.batch_size = 100

            for object_id in object_ids:
                batch.delete_data_object(
                    class_name=class_name,
                    uuid=object_id
                )

    def close(self) -> None:
        """Close the client connection."""
        try:
            self.client._connection.close()
        except Exception:
            pass
