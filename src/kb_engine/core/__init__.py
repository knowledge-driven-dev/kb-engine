"""Core domain models and interfaces for KB-Engine."""

from kb_engine.core.exceptions import (
    ChunkingError,
    ConfigurationError,
    ExtractionError,
    KBPodError,
    RepositoryError,
    ValidationError,
)
from kb_engine.core.models import (
    Chunk,
    Document,
    Edge,
    EdgeType,
    Embedding,
    Node,
    NodeType,
    SearchFilters,
    SearchResult,
)

__all__ = [
    # Models
    "Document",
    "Chunk",
    "Embedding",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    "SearchFilters",
    "SearchResult",
    # Exceptions
    "KBPodError",
    "ConfigurationError",
    "ValidationError",
    "RepositoryError",
    "ChunkingError",
    "ExtractionError",
]
