"""Search-related models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from kb_engine.core.models.document import Chunk


class RetrievalMode(str, Enum):
    """Retrieval strategy mode."""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


class SearchFilters(BaseModel):
    """Filters for search queries."""

    # Document filters
    document_ids: list[UUID] | None = None
    domains: list[str] | None = None
    tags: list[str] | None = None

    # Chunk type filters
    chunk_types: list[str] | None = None

    # Date filters
    created_after: datetime | None = None
    created_before: datetime | None = None

    # Metadata filters (key-value pairs)
    metadata: dict[str, Any] | None = None

    # Graph filters
    node_types: list[str] | None = None
    max_hops: int = 2

    class Config:
        frozen = True


class SearchResult(BaseModel):
    """A single search result."""

    chunk: Chunk
    score: float = 0.0
    retrieval_mode: RetrievalMode = RetrievalMode.VECTOR

    # Additional context from graph traversal
    graph_context: list[dict[str, Any]] = Field(default_factory=list)

    # Explanation of why this result matched
    explanation: str | None = None

    class Config:
        frozen = False


class SearchResponse(BaseModel):
    """Response from a search query."""

    query: str
    results: list[SearchResult]
    total_count: int
    retrieval_mode: RetrievalMode
    filters_applied: SearchFilters | None = None
    processing_time_ms: float | None = None

    class Config:
        frozen = False
