"""Search-related models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
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

    # KDD status filters
    # By default, only "approved" documents are included
    # Use include_statuses to expand (e.g., ["approved", "proposed"])
    # Use exclude_statuses to explicitly exclude
    include_statuses: list[str] | None = None  # None = ["approved"] by default
    exclude_statuses: list[str] | None = None
    include_all_statuses: bool = False  # Override to include everything

    # Date filters
    created_after: datetime | None = None
    created_before: datetime | None = None

    # Metadata filters (key-value pairs)
    metadata: dict[str, Any] | None = None

    class Config:
        frozen = True

    def get_effective_statuses(self) -> list[str] | None:
        """Get the list of statuses to include in search.

        Returns None if all statuses should be included.
        """
        if self.include_all_statuses:
            return None

        if self.include_statuses:
            statuses = set(self.include_statuses)
        else:
            statuses = {"approved"}  # Default

        if self.exclude_statuses:
            statuses -= set(self.exclude_statuses)

        return list(statuses) if statuses else None


class DocumentReference(BaseModel):
    """A reference to a document section returned by retrieval.

    Instead of returning raw content, we return URLs pointing to
    the exact section so an external agent can read the source directly.
    """

    url: str
    document_path: str
    section_anchor: str | None = None
    title: str
    section_title: str | None = None
    score: float = 0.0
    snippet: str = ""
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)
    chunk_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieval_mode: RetrievalMode = RetrievalMode.VECTOR

    # KDD lifecycle
    kdd_status: str = "approved"
    kdd_version: str | None = None


class RetrievalResponse(BaseModel):
    """Response from a retrieval query."""

    query: str
    references: list[DocumentReference]
    total_count: int
    processing_time_ms: float | None = None
