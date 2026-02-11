# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Varity is a Python tool for ingesting ESCO (European Skills, Competences, Qualifications, and Occupations) taxonomy data into a Weaviate vector database and performing semantic search over it. It supports data ingestion, semantic search, and English-to-Hebrew translation of ESCO concepts.

## Build and Run Commands

```bash
# Install package (editable mode)
pip install -e .

# Start all services via Docker
docker-compose up -d

# Start specific services
docker-compose up weaviate t2v-transformers    # Vector DB + transformer inference
docker-compose up varity-init                    # Run ingestion
docker-compose up varity-search                  # Start search service (port 8000)
```

### CLI Usage

```bash
# Ingestion
python src/esco_cli.py ingest --config config/weaviate_config.yaml
python src/esco_cli.py ingest --config config/weaviate_config.yaml --force-reingest
python src/esco_cli.py ingest --config config/weaviate_config.yaml --classes Skill Occupation

# Search
python src/esco_cli.py search --query "python programming"
python src/esco_cli.py search --query "python programming" --type Skill --limit 5 --certainty 0.7

# Translation
python src/esco_cli.py translate --type Skill --property prefLabel --batch-size 50
```

### Entry Points (from setup.py)

- `varity-search` → `src.application.services.search_application_service:main`

## Testing

```bash
pytest                                    # Run all tests
pytest tests/test_ingestion_service.py    # Single test file
pytest -v                                 # Verbose output
pytest tests/test_integration.py          # Integration tests
pytest tests/test_long_running_ingestion.py  # Long-running tests
```

Test fixtures are in `tests/conftest.py` and include mock Weaviate clients, test configurations with shorter timeouts, and mock progress objects.

## Architecture

The project uses a layered architecture with core domain entities, application services, and infrastructure implementations.

### Primary Modules

- `src/esco_ingest.py` — `WeaviateIngestor`: Main ingestion logic for loading ESCO data into Weaviate
- `src/weaviate_semantic_search.py` — `VaritySemanticSearch`: Semantic search over Weaviate data
- `src/esco_cli.py` — Click-based CLI entry point for ingestion, search, and translation commands

### Layers

**Core** (`src/core/`) — Domain entities and interfaces. No external dependencies.
- `entities/`: `IngestionState`, `IngestionConfig`, `IngestionProgress`, search entities, ESCO entities
- `interfaces/`: `repository_interface.py`, `service_interface.py`, `client_interface.py`

**Domain** (`src/domain/`) — Pure business logic.
- `ingestion/`: Ingestion domain service, state management service, validation domain service

**Application** (`src/application/`) — Orchestration layer.
- `services/`: `IngestionService`, search application service

**Infrastructure** (`src/infrastructure/`) — Technical implementations.
- `database/weaviate/`: Weaviate client
- `external/`: Embedding utilities
- `config/`: Configuration validation, environment config
- `ingestion/`: Init ingestion, data reader, entity ingestor, relation builder, orchestrator

**Shared** (`src/shared/`) — Cross-cutting concerns.
- `di/`: Dependency injection container, service registry, lifetime manager
- `exceptions/`: Error context, recovery strategies
- `logging/`: Structured logger, logger interface
- `validation/`: Validator interface, validation rules

### Key Design Patterns

- **Repository Pattern**: Data access abstracted through interfaces in `core/interfaces/`
- **Dependency Injection**: `src/shared/di/` container for loose coupling
- **State Management**: Ingestion tracks state (`not_started`, `in_progress`, `completed`, `failed`) via Weaviate Metadata class with heartbeat-based staleness detection (threshold: 2 hours)
- **Factory Pattern**: Database factory in `infrastructure/database/factory.py`

## Configuration

Primary config: `config/weaviate_config.yaml` with `default` and `cloud` profiles.

Key settings: Weaviate URL, batch size, embedding model (`multi-qa-MiniLM-L6-cos-v1`), translation model (`Helsinki-NLP/opus-mt-en-he`), staleness thresholds, device selection (`auto`/`cpu`/`cuda`/`mps`).

Weaviate schemas defined in `resources/schemas/` as YAML files (occupation, skill, isco_group, skill_collection, skill_group, metadata, references).

ESCO source data lives in `data/esco/` as CSV files.

## Documentation

Project documentation lives in `docs/`:
- `esco_schema.md` — ESCO schema reference
- `weaviate_queries.md` — Weaviate query examples
- `project_overview.md` — Project overview
- `python_docstring_guide.md` — Docstring style guide
- `architecture.svg` — Architecture diagram

## Code Navigation

When searching for definitions, references, or understanding code structure, prefer the GKG Knowledge Graph MCP tools (`search_codebase_definitions`, `read_definitions`, `get_references`, `get_definition`, `repo_map`) over Glob and Grep. These tools provide structured, semantically-aware results (function signatures, call sites, dependency graphs) that are faster and more precise than file-level pattern matching. Fall back to Glob/Grep only when the knowledge graph does not cover the needed information (e.g., searching inside comments, config files, or non-code assets).

## Conventions

- **Python 3.10+** required
- **Formatting**: Black (88 char line length)
- **Linting**: Ruff/Flake8 + Pylint
- **Type hints**: Required on all functions (MyPy, avoid `Any`)
- **Docstrings**: Google-style, mandatory for public APIs (see `docs/python_docstring_guide.md`)
- **Commits**: Conventional Commits format (`feat:`, `fix:`, etc.)
- **Terminology**: Use "URI" not "URL" for ESCO identifiers, "concept" over "entity" for ESCO items, "taxonomy" for ESCO structure, "ingestion" for data loading
- **Weaviate client version**: v3 API (`weaviate-client 3.26.7`)
- **PYTHONPATH**: Must include project root (set to `/app` in Docker)

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| weaviate | 8080, 50051 | Vector database (v1.31.0) |
| t2v-transformers | — | Sentence transformer inference |
| varity-init | — | One-shot ingestion container |
| varity-search | 8000 | Search service with `/health` endpoint |
| varity-cli | — | Manual CLI operations |
