"""Domain events for KDD.

All events are frozen dataclasses aligned with their spec definitions
under ``specs/01-domain/events/``.

Each event is immutable (frozen=True) and carries the payload described
in the corresponding EVT-* spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer, RetrievalStrategy


# ---------------------------------------------------------------------------
# Document lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentDetected:
    """A spec file with valid front-matter was found in /specs.

    Spec: EVT-KDDDocument-Detected
    """

    source_path: str
    source_hash: str
    kind: KDDKind
    layer: KDDLayer
    detected_at: datetime


@dataclass(frozen=True)
class DocumentParsed:
    """A KDDDocument was successfully parsed by its kind extractor.

    Spec: EVT-KDDDocument-Parsed
    """

    document_id: str
    source_path: str
    kind: KDDKind
    front_matter: dict[str, Any]
    section_count: int
    wiki_link_count: int
    parsed_at: datetime


@dataclass(frozen=True)
class DocumentIndexed:
    """A KDDDocument completed the full indexing pipeline.

    Spec: EVT-KDDDocument-Indexed
    """

    document_id: str
    source_path: str
    kind: KDDKind
    node_id: str
    edge_count: int
    embedding_count: int
    index_level: IndexLevel
    duration_ms: int
    indexed_at: datetime


@dataclass(frozen=True)
class DocumentStale:
    """A previously-indexed KDDDocument was modified on disk.

    Spec: EVT-KDDDocument-Stale
    """

    document_id: str
    source_path: str
    previous_hash: str
    current_hash: str
    detected_at: datetime


@dataclass(frozen=True)
class DocumentDeleted:
    """A previously-indexed KDDDocument was removed from the filesystem.

    Spec: EVT-KDDDocument-Deleted
    """

    document_id: str
    source_path: str
    node_id: str
    edge_count: int
    embedding_count: int
    deleted_at: datetime


# ---------------------------------------------------------------------------
# Merge events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeRequested:
    """A merge of multiple developer indexes was requested.

    Spec: EVT-Index-MergeRequested
    """

    merge_id: UUID
    source_manifests: list[str] = field(default_factory=list)
    developer_ids: list[str] = field(default_factory=list)
    target_version: str = ""
    requested_at: datetime = field(default_factory=datetime.now)
    requested_by: str = ""


@dataclass(frozen=True)
class MergeCompleted:
    """A merge of indexes completed successfully.

    Spec: EVT-Index-MergeCompleted
    """

    merge_id: UUID
    merged_manifest_id: str
    source_count: int
    total_nodes: int
    total_edges: int
    total_embeddings: int
    conflicts_resolved: int
    duration_ms: int
    completed_at: datetime


# ---------------------------------------------------------------------------
# Query lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryReceived:
    """A retrieval query was received from an agent or developer.

    Spec: EVT-RetrievalQuery-Received
    """

    query_id: UUID
    strategy: RetrievalStrategy
    query_text: str | None = None
    root_node: str | None = None
    caller: str | None = None
    received_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class QueryCompleted:
    """A retrieval query was resolved successfully.

    Spec: EVT-RetrievalQuery-Completed
    """

    query_id: UUID
    strategy: RetrievalStrategy
    total_results: int
    top_score: float
    total_tokens: int
    duration_ms: int
    completed_at: datetime


@dataclass(frozen=True)
class QueryFailed:
    """A retrieval query failed during validation or resolution.

    Spec: EVT-RetrievalQuery-Failed
    """

    query_id: UUID
    strategy: RetrievalStrategy
    error_code: str
    error_message: str
    phase: str  # "validation" or "resolution"
    duration_ms: int
    failed_at: datetime
