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

- `varity-cli` → `src.presentation.cli.esco_cli:cli`
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

The project follows **Clean Architecture** with four layers. Dependencies point inward: Presentation → Application → Domain/Core ← Infrastructure.

### Layers

**Core** (`src/core/`) — Domain entities and interfaces. No external dependencies.
- `entities/`: `IngestionState`, `IngestionConfig`, `IngestionProgress`, search entities, ESCO entities
- `interfaces/`: `repository_interface.py`, `service_interface.py`, `client_interface.py`

**Domain** (`src/domain/`) — Pure business logic, framework-independent.
- `ingestion/`: Ingestion domain service, state management, validation
- `search/`: Search domain service

**Application** (`src/application/`) — Orchestration layer.
- `services/`: `IngestionService`, search application service
- `handlers/`: Request/response handling for ingestion and search

**Infrastructure** (`src/infrastructure/`) — Technical implementations.
- `database/weaviate/`: Weaviate client and repository implementations
- `external/`: Embedding client, translation client
- `config/`: Configuration management (profiles: `default`, `cloud`)
- `ingestion/`: Init ingestion infrastructure

**Presentation** (`src/presentation/`) — User-facing interfaces.
- `cli/commands/`: Click-based CLI commands for ingestion, search, translation
- `containers/`: Docker container initialization, health checks

**Shared** (`src/shared/`) — Cross-cutting concerns.
- `di/`: Dependency injection container and service registry
- `exceptions/`: Error handler, error context, recovery strategies
- `logging/`: Structured logger with formatters
- `validation/`: Validation engine and rules

### Legacy Modules

`src/esco_ingest.py` and `src/weaviate_semantic_search.py` are older modules still in use alongside the clean architecture layers.

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

## Conventions

- **Python 3.10+** required
- **Formatting**: Black (88 char line length)
- **Linting**: Ruff/Flake8 + Pylint
- **Type hints**: Required on all functions (MyPy, avoid `Any`)
- **Docstrings**: Google-style, mandatory for public APIs (see `python_docstring_guide.md`)
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
