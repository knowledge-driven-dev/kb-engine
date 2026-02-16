"""Domain entities for KDD.

All entities are Pydantic BaseModels aligned with their spec definitions
under ``specs/01-domain/entities/``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from kdd.domain.enums import (
    DocumentStatus,
    IndexLevel,
    KDDKind,
    KDDLayer,
    QueryStatus,
    RetrievalStrategy,
)


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class Section(BaseModel):
    """A Markdown section extracted from a KDD document."""

    heading: str
    level: int
    content: str
    path: str = ""  # hierarchical path e.g. "descripcion.atributos"


class IndexStats(BaseModel):
    """Aggregate counts stored in an IndexManifest."""

    nodes: int = 0
    edges: int = 0
    embeddings: int = 0
    enrichments: int = 0


class ScoredNode(BaseModel):
    """A graph node scored by the retrieval engine."""

    node_id: str
    score: float
    snippet: str | None = None
    match_source: str  # "semantic", "graph", "lexical", "fusion"


class LayerViolation(BaseModel):
    """A detected layer-dependency violation between two nodes."""

    from_node: str
    to_node: str
    from_layer: KDDLayer
    to_layer: KDDLayer
    edge_type: str


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class KDDDocument(BaseModel):
    """A parsed KDD spec file — the atomic input to the indexing pipeline.

    Spec: specs/01-domain/entities/KDDDocument.md
    """

    id: str
    kind: KDDKind
    source_path: str
    source_hash: str
    layer: KDDLayer
    front_matter: dict[str, Any]
    sections: list[Section]
    wiki_links: list[str] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.DETECTED
    indexed_at: datetime | None = None
    domain: str | None = None


class GraphNode(BaseModel):
    """A node in the knowledge graph, produced by indexing a KDDDocument.

    Spec: specs/01-domain/entities/GraphNode.md
    """

    id: str  # "{Kind}:{DocumentId}" e.g. "Entity:Pedido"
    kind: KDDKind
    source_file: str
    source_hash: str
    layer: KDDLayer
    status: str = "draft"  # artifact status (draft/review/approved/deprecated)
    aliases: list[str] = Field(default_factory=list)
    domain: str | None = None
    indexed_fields: dict[str, Any] = Field(default_factory=dict)
    indexed_at: datetime | None = None


class GraphEdge(BaseModel):
    """A typed, directed relationship between two GraphNodes.

    Spec: specs/01-domain/entities/GraphEdge.md
    """

    from_node: str
    to_node: str
    edge_type: str  # SCREAMING_SNAKE = structural, snake_case = business
    source_file: str
    extraction_method: str  # "wiki_link", "section_content", "implicit"
    metadata: dict[str, Any] = Field(default_factory=dict)
    layer_violation: bool = False
    bidirectional: bool = False


class Embedding(BaseModel):
    """A semantic vector generated from a paragraph of a KDDDocument.

    Spec: specs/01-domain/entities/Embedding.md
    """

    id: str  # "{document_id}:{section_path}:{chunk_index}"
    document_id: str
    document_kind: KDDKind
    section_path: str
    chunk_index: int
    raw_text: str
    context_text: str
    vector: list[float]
    model: str
    dimensions: int
    text_hash: str
    generated_at: datetime


class IndexManifest(BaseModel):
    """Metadata for a generated index stored in ``.kdd-index/manifest.json``.

    Spec: specs/01-domain/entities/IndexManifest.md
    """

    version: str  # semver
    kdd_version: str
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    indexed_at: datetime
    indexed_by: str
    structure: str = "single-domain"  # "single-domain" | "multi-domain"
    index_level: IndexLevel
    stats: IndexStats = Field(default_factory=IndexStats)
    domains: list[str] = Field(default_factory=list)
    git_commit: str | None = None


class RetrievalQuery(BaseModel):
    """A query from an AI agent or developer to the retrieval engine.

    Spec: specs/01-domain/entities/RetrievalQuery.md
    """

    id: UUID
    strategy: RetrievalStrategy
    query_text: str | None = None
    root_node: str | None = None
    depth: int = 2
    edge_types: list[str] = Field(default_factory=list)
    include_kinds: list[KDDKind] = Field(default_factory=list)
    include_layers: list[KDDLayer] = Field(default_factory=list)
    respect_layers: bool = True
    min_score: float = 0.7
    limit: int = 10
    max_tokens: int = 8000
    status: QueryStatus = QueryStatus.RECEIVED
    received_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    caller: str | None = None


class RetrievalResult(BaseModel):
    """The response returned by the retrieval engine for a RetrievalQuery.

    Spec: specs/01-domain/entities/RetrievalResult.md
    """

    query_id: UUID
    strategy: RetrievalStrategy
    results: list[ScoredNode]
    graph_expansion: list[GraphEdge] = Field(default_factory=list)
    total_nodes: int
    total_tokens: int | None = None
    layer_violations: list[LayerViolation] = Field(default_factory=list)
