"""Document and Chunk models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentStatus(str, Enum):
    """Document processing status (internal workflow)."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class KDDStatus(str, Enum):
    """KDD document lifecycle status (from frontmatter).

    Controls visibility in search results:
    - draft: Work in progress, not ready for review
    - proposed: Ready for review, not yet approved
    - approved: Official, included in default searches (alias: active)
    - deprecated: Obsolete, excluded by default but preserved
    """

    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    DEPRECATED = "deprecated"

    @classmethod
    def from_string(cls, value: str | None) -> "KDDStatus":
        """Parse status from string, handling aliases."""
        if value is None:
            return cls.APPROVED  # Default
        normalized = value.lower().strip()
        # Handle aliases
        if normalized == "active":
            return cls.APPROVED
        try:
            return cls(normalized)
        except ValueError:
            return cls.APPROVED  # Default for unknown values


class ChunkType(str, Enum):
    """Semantic chunk types as defined in ADR-0002."""

    ENTITY = "entity"
    USE_CASE = "use_case"
    RULE = "rule"
    PROCESS = "process"
    DEFAULT = "default"


class Document(BaseModel):
    """A document in the knowledge base.

    Represents a source document (typically a KDD markdown file) that
    contains knowledge to be indexed and retrieved.
    """

    id: UUID = Field(default_factory=uuid4)

    @field_validator("id", mode="before")
    @classmethod
    def _ensure_id(cls, v: Any) -> Any:
        return v if v is not None else uuid4()

    external_id: str | None = None
    title: str
    content: str
    source_path: str | None = None
    mime_type: str = "text/markdown"

    # Metadata extracted from frontmatter or inferred
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    domain: str | None = None

    # KDD lifecycle fields (from frontmatter)
    kdd_status: KDDStatus = KDDStatus.APPROVED
    kdd_version: str | None = None

    # Git-aware fields
    repo_name: str | None = None
    relative_path: str | None = None
    git_commit: str | None = None
    git_remote_url: str | None = None

    # Processing state
    status: DocumentStatus = DocumentStatus.PENDING
    content_hash: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = None

    class Config:
        frozen = False


class Chunk(BaseModel):
    """A semantic chunk extracted from a document.

    Chunks are the atomic units for embedding and retrieval.
    Each chunk has a semantic type that determines how it was
    extracted and how it should be processed.
    """

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    sequence: int = 0

    # Content
    content: str
    chunk_type: ChunkType = ChunkType.DEFAULT

    # Position in source document
    start_offset: int | None = None
    end_offset: int | None = None
    heading_path: list[str] = Field(default_factory=list)

    # Section anchor (computed from heading_path)
    section_anchor: str | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int | None = None

    # Embedding reference
    embedding_id: UUID | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = False
