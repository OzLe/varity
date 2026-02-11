# Varity: Complete Clean Architecture Migration (Phase 4 Remaining)

## Context

Phases 1-3 and Phase 4 items 4.1, 4.2, 4.4, 4.5, 4.7, 4.8 are **DONE**. All 35 key modules import successfully. The remaining work completes the Clean Architecture migration:

- **4.6**: Implement `IngestionApplicationService` (6 missing interface methods)
- **4.3**: Decompose `WeaviateIngestor` God Object (825 lines → 4 focused modules)
- **4.9**: Rewrite tests (fix fixtures, make tests pass)
- **4.10**: Deprecate legacy modules (facade pattern, update entry point)

**Root problem**: `IngestionApplicationService` extends `IngestionServiceInterface` but implements NONE of the 6 required abstract methods. It has 3 document-processing methods that aren't in the interface. Tests fail with "Can't instantiate abstract class".

---

## Step 1: Implement IngestionApplicationService (4.6)

### File: `src/application/services/ingestion_application_service.py`

**Update constructor** to accept all needed dependencies:
```python
def __init__(self, repository, client, ingestion_domain_service,
             state_management_service, config: IngestionConfig,
             ingestor=None):  # Legacy ingestor for delegation
```

**Implement 6 missing methods** (each ~20-40 lines):

| Method | Delegates To | Returns |
|--------|-------------|---------|
| `get_current_state()` | `client.get_ingestion_status()` → `StateManagementService.determine_ingestion_state()` | `IngestionState` |
| `should_run_ingestion(force_reingest)` | `get_current_state()` → `IngestionDomainService.make_ingestion_decision()` | `IngestionDecision` |
| `validate_prerequisites()` | `client.is_connected()`, `client.ensure_schema()`, `IngestionDomainService.validate_ingestion_prerequisites()` | `ValidationResult` |
| `run_ingestion(progress_callback)` | Sets metadata via `client.set_ingestion_metadata()`, delegates to `self.ingestor.run_simple_ingestion()` | `IngestionResult` |
| `verify_completion()` | `get_current_state()`, `client.get_repository(class_name).count_objects()` for each class | `ValidationResult` |
| `get_ingestion_metrics()` | `client.get_repository().count_objects()` per class, `client.get_ingestion_status()` | `Dict[str, Any]` |

**Remove** the 3 non-interface methods (`process_document`, `get_processing_status`, `retry_processing`).

### File: `src/domain/ingestion/validation_domain_service.py`

Add 2 missing methods called by `IngestionDomainService.validate_ingestion_prerequisites()`:
- `validate_config(config: IngestionConfig) -> ValidationResult` — delegate to config's own validation
- `validate_data_files(data_dir, required_files) -> ValidationResult` — check files exist and are readable

### File: `src/core/entities/ingestion_entity.py`

Add `classes_to_ingest` field to `IngestionConfig` (default: `["Occupation", "Skill", "ISCOGroup", "SkillGroup", "SkillCollection"]`).

Ensure `ValidationResult` has: `is_valid`, `errors` (list), `warnings` (list), `checks_performed` (list), `details` (dict), plus `add_error()`, `add_warning()`, `add_success()` helper methods.

---

## Step 2: Decompose WeaviateIngestor (4.3)

Create 4 new files under `src/infrastructure/ingestion/`:

### `esco_data_reader.py` (~120 lines)
- `ESCODataReader(data_dir, batch_size)`
- `process_csv_in_batches(filename, process_func, heartbeat_callback)` — CSV batching with tqdm
- `standardize_hierarchy_columns(df)` — static, rename broaderUri/narrowerUri variants
- `standardize_collection_relation_columns(df)` — static, rename conceptSchemeUri/skillUri variants

Extracted from: `esco_ingest.py` lines 64-88, 179-238, 240-266

### `entity_ingestor.py` (~180 lines)
- `EntityIngestor(client, data_reader, heartbeat_callback)`
- `ingest_isco_groups()`, `ingest_occupations()`, `ingest_skills()`, `ingest_skill_groups()`, `ingest_skill_collections()`
- Each uses `data_reader.process_csv_in_batches()` + `client.batch_add_objects()`

Extracted from: `esco_ingest.py` lines 309-613

### `relation_builder.py` (~200 lines)
- `RelationBuilder(client, data_reader)` with UUID cache
- `_prefetch_uuids(class_name)` — cached UUID pre-fetch
- `create_skill_relations()`, `create_hierarchical_relations()`, `create_isco_group_relations()`, `create_skill_collection_relations()`, `create_skill_skill_relations()`, `create_broader_skill_relations()`
- Each uses pre-fetched UUID sets + `client.batch_add_references()`

Extracted from: `esco_ingest.py` lines 416-738

### `ingestion_orchestrator.py` (~80 lines)
- `IngestionOrchestrator(client, data_dir, batch_size, progress_callback)`
- `run_complete_ingestion() -> dict` — 12-step pipeline (schema + 5 entities + 6 relations)
- Creates `ESCODataReader`, `EntityIngestor`, `RelationBuilder` internally
- Updates heartbeat metadata at each step

Extracted from: `esco_ingest.py` lines 740-772

### Update `esco_ingest.py` — facade with deprecation
- Add `DeprecationWarning` in `__init__`
- `run_simple_ingestion()` delegates to `IngestionOrchestrator.run_complete_ingestion()`
- Keep all other methods for backwards compatibility (unused by orchestrator)

---

## Step 3: Fix Tests (4.9)

### `tests/conftest.py`
- Add `ingestion_config` fixture returning `IngestionConfig` with test values
- Update `ingestion_service` fixture: construct `IngestionApplicationService` with all 6 args (mock_repository, mock_weaviate_client, IngestionDomainService(), StateManagementService(), ingestion_config, mock_ingestor)
- Add `mock_repository` fixture
- Keep existing `mock_weaviate_client` but add mocks for: `is_connected()`, `ensure_schema()`, `get_ingestion_status()`, `set_ingestion_metadata()`, `check_object_exists()`, `get_repository()`

### `tests/test_ingestion_service.py` (~12 tests)
Rewrite all tests to call the actual interface methods:
- `test_should_run_ingestion_when_not_started` — mock status "not_started", assert `decision.should_run`
- `test_should_not_run_ingestion_when_completed` — mock status "completed", assert `not decision.should_run`
- `test_should_run_ingestion_when_stale` — mock old timestamp, assert `decision.should_run`
- `test_should_not_run_ingestion_when_active` — mock recent timestamp, assert `not decision.should_run`
- `test_force_reingest_overrides_checks` — mock "completed", pass `force_reingest=True`, assert `decision.should_run`
- `test_validate_prerequisites` — mock connected, assert `validation.is_valid`
- `test_validate_prerequisites_fails` — mock disconnected, assert `not validation.is_valid`
- `test_run_ingestion_success` — assert `result.success`
- `test_run_ingestion_handles_failure` — mock ingestor raises, assert `not result.success`
- `test_verify_completion_success` — mock completed + data counts > 0
- `test_get_ingestion_metrics` — mock repo counts, assert "total_objects" in metrics

### `tests/test_long_running_ingestion.py` (~5 tests)
Rewrite to use interface methods:
- `test_heartbeat_based_staleness_detection` — old timestamp → should_run
- `test_ingestion_runs_with_valid_prerequisites` — validate + run
- `test_ingestion_state_transitions` — NOT_STARTED → IN_PROGRESS → COMPLETED
- `test_verify_completion_with_data` — completed + counts
- `test_metrics_collection` — verify metric keys

---

## Step 4: Deprecate Legacy (4.10)

### `src/infrastructure/ingestion/init_ingestion.py`
- Try importing `IngestionOrchestrator` first, fall back to `WeaviateIngestor`
- Use orchestrator path: `client.ensure_schema()` → `IngestionOrchestrator(client, data_dir).run_complete_ingestion()`
- Keep legacy fallback for safety

### Leave `src/weaviate_semantic_search.py` untouched
It's the working search path, independent of ingestion.

---

## Execution Order

```
Step 1 (4.6) → Step 2 (4.3) → Step 3 (4.9) → Step 4 (4.10)
```

Step 1 must go first (tests depend on the interface methods). Step 2 creates the modules that Step 4 uses. Step 3 verifies everything works.

## Verification

```bash
# All imports work
python -c "from src.application.services.ingestion_application_service import IngestionApplicationService; print('OK')"
python -c "from src.infrastructure.ingestion.ingestion_orchestrator import IngestionOrchestrator; print('OK')"

# All tests pass
pytest tests/ -v

# Docker still works
docker-compose build && docker-compose up -d
curl http://localhost:8000/health
```

## Critical Files

| File | Action |
|------|--------|
| `src/application/services/ingestion_application_service.py` | Rewrite — implement 6 interface methods |
| `src/domain/ingestion/validation_domain_service.py` | Add 2 missing methods |
| `src/core/entities/ingestion_entity.py` | Add fields to IngestionConfig, ensure ValidationResult helpers |
| `src/infrastructure/ingestion/esco_data_reader.py` | **New** — CSV reading |
| `src/infrastructure/ingestion/entity_ingestor.py` | **New** — entity ingestion |
| `src/infrastructure/ingestion/relation_builder.py` | **New** — relation creation |
| `src/infrastructure/ingestion/ingestion_orchestrator.py` | **New** — orchestration |
| `src/esco_ingest.py` | Add deprecation, delegate to orchestrator |
| `src/infrastructure/ingestion/init_ingestion.py` | Use orchestrator, fallback to legacy |
| `tests/conftest.py` | Fix fixtures |
| `tests/test_ingestion_service.py` | Rewrite tests |
| `tests/test_long_running_ingestion.py` | Rewrite tests |
