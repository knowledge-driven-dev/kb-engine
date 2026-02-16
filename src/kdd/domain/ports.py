"""Port definitions (hexagonal architecture).

Each Protocol defines a boundary that infrastructure adapters must satisfy.
The domain and application layers depend only on these Protocols, never on
concrete implementations.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from kdd.domain.entities import (
    Embedding,
    GraphEdge,
    GraphNode,
    IndexManifest,
)


# ---------------------------------------------------------------------------
# Storage ports
# ---------------------------------------------------------------------------


@runtime_checkable
class ArtifactStore(Protocol):
    """Read/write .kdd-index/ artifacts on disk."""

    def write_manifest(self, manifest: IndexManifest) -> None: ...
    def read_manifest(self) -> IndexManifest | None: ...
    def write_node(self, node: GraphNode) -> None: ...
    def read_node(self, node_id: str) -> GraphNode | None: ...
    def append_edges(self, edges: list[GraphEdge]) -> None: ...
    def read_edges(self) -> list[GraphEdge]: ...
    def write_embeddings(self, embeddings: list[Embedding]) -> None: ...
    def read_embeddings(self, document_id: str) -> list[Embedding]: ...
    def read_all_nodes(self) -> list[GraphNode]: ...
    def read_all_embeddings(self) -> list[Embedding]: ...
    def delete_document_artifacts(self, document_id: str) -> None: ...


@runtime_checkable
class GraphStore(Protocol):
    """In-memory graph loaded from artifacts for querying."""

    def load(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None: ...
    def get_node(self, node_id: str) -> GraphNode | None: ...
    def has_node(self, node_id: str) -> bool: ...
    def traverse(
        self,
        root: str,
        depth: int,
        edge_types: list[str] | None = None,
        respect_layers: bool = True,
    ) -> tuple[list[GraphNode], list[GraphEdge]]: ...
    def text_search(
        self,
        query: str,
        fields: list[str] | None = None,
    ) -> list[GraphNode]: ...
    def neighbors(self, node_id: str) -> list[GraphNode]: ...
    def incoming_edges(self, node_id: str) -> list[GraphEdge]: ...
    def outgoing_edges(self, node_id: str) -> list[GraphEdge]: ...
    def reverse_traverse(
        self,
        root: str,
        depth: int,
    ) -> list[tuple[GraphNode, list[GraphEdge]]]: ...
    def all_edges(self) -> list[GraphEdge]: ...
    def find_violations(self) -> list[GraphEdge]: ...


@runtime_checkable
class VectorStore(Protocol):
    """In-memory vector index loaded from artifacts for semantic search."""

    def load(self, embeddings: list[Embedding]) -> None: ...
    def search(
        self,
        vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]: ...  # (embedding_id, score)


# ---------------------------------------------------------------------------
# Embedding port
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbeddingModel(Protocol):
    """Generates embedding vectors from text."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def encode(self, texts: list[str]) -> list[list[float]]: ...


# ---------------------------------------------------------------------------
# Event bus port
# ---------------------------------------------------------------------------


@runtime_checkable
class EventBus(Protocol):
    """Publish/subscribe in-memory event bus."""

    def publish(self, event: Any) -> None: ...
    def subscribe(self, event_type: type, handler: Any) -> None: ...


# ---------------------------------------------------------------------------
# External integration ports
# ---------------------------------------------------------------------------


@runtime_checkable
class AgentClient(Protocol):
    """Communicates with an AI agent for L3 enrichment (CMD-003)."""

    def enrich(self, node: GraphNode, context: str) -> dict[str, Any]: ...


@runtime_checkable
class Transport(Protocol):
    """Push/pull .kdd-index/ artifacts to a remote (CMD-005)."""

    def push(self, index_path: str, remote: str) -> None: ...
    def pull(self, remote: str, target_path: str) -> None: ...
