# KB-Engine

A hybrid RAG (Retrieval-Augmented Generation) system for knowledge base management.

## Overview

KB-Engine is designed to index, store, and retrieve knowledge from structured documents (KDD - Knowledge Domain Documents). It implements a tri-store architecture:

- **PostgreSQL**: Traceability store for documents, chunks, and metadata
- **Qdrant**: Vector store for semantic similarity search
- **Neo4j**: Graph store for entity relationships

## Features

- Semantic chunking with specialized strategies (entities, use cases, rules, processes)
- Multi-modal entity extraction (frontmatter, patterns, LLM)
- Hybrid retrieval combining vector and graph search
- RESTful API with FastAPI
- Full traceability and audit capabilities

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd kb-engine

# Run the setup script
chmod +x scripts/setup_dev.sh
./scripts/setup_dev.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Start infrastructure
docker compose -f docker/docker-compose.yml up -d

# Run the server
make dev
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make test-cov
```

## Project Structure

```
kb-engine/
├── src/kb_engine/
│   ├── core/           # Domain models and interfaces
│   ├── repositories/   # Data store implementations
│   ├── chunking/       # Semantic chunking strategies
│   ├── extraction/     # Entity extraction pipeline
│   ├── embedding/      # Embedding generation
│   ├── pipelines/      # Indexation and inference pipelines
│   ├── services/       # Business logic
│   ├── api/            # FastAPI REST API
│   └── config/         # Configuration
├── tests/
├── docker/
├── migrations/
└── docs/design/        # ADRs and design documents
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/v1/inference/search` - Search the knowledge base
- `POST /api/v1/indexing/documents` - Index a new document
- `GET /api/v1/indexing/documents` - List documents
- `POST /api/v1/curation/nodes` - Manage knowledge graph nodes

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_HOST/PORT`: Qdrant connection
- `NEO4J_URI/USER/PASSWORD`: Neo4j connection
- `OPENAI_API_KEY`: For embeddings and LLM extraction

## Architecture

See the design documents in `docs/design/` for detailed ADRs:

- ADR-0001: Repository pattern for data stores
- ADR-0002: Semantic chunking strategy
- ADR-0003: Entity extraction pipeline

## License

MIT
