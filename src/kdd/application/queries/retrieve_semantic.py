"""QRY-002 — RetrieveSemantic.

Semantic search over embeddings, finding document fragments most similar
to query text.  Corresponds to ``POST /v1/retrieve/search``.

Spec: specs/02-behavior/queries/QRY-002-RetrieveSemantic.md
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kdd.domain.entities import ScoredNode
from kdd.domain.enums import KDDKind, KDDLayer
from kdd.domain.ports import EmbeddingModel, GraphStore, VectorStore


@dataclass
class SemanticQueryInput:
    query_text: str
    include_kinds: list[KDDKind] | None = None
    include_layers: list[KDDLayer] | None = None
    min_score: float = 0.7
    limit: int = 10


@dataclass
class SemanticQueryResult:
    results: list[ScoredNode]
    total_results: int
    embedding_model: str


def retrieve_semantic(
    query: SemanticQueryInput,
    embedding_model: EmbeddingModel,
    vector_store: VectorStore,
    graph_store: GraphStore,
) -> SemanticQueryResult:
    """Execute a semantic search query (QRY-002).

    Raises ValueError if query_text is too short.
    """
    if len(query.query_text.strip()) < 3:
        raise ValueError("QUERY_TOO_SHORT: query_text must be at least 3 characters")

    # Encode query
    vectors = embedding_model.encode([query.query_text])
    query_vector = vectors[0]

    # Search vector store
    matches = vector_store.search(
        vector=query_vector,
        limit=query.limit * 3,  # over-fetch to account for post-filtering
        min_score=query.min_score,
    )

    # Resolve embedding IDs to nodes and filter
    seen_nodes: set[str] = set()
    results: list[ScoredNode] = []

    for emb_id, score in matches:
        # Embedding ID format: "{document_id}:chunk-{n}"
        doc_id = emb_id.rsplit(":chunk-", 1)[0] if ":chunk-" in emb_id else emb_id.split(":")[0]

        # Find the node for this document
        node = _find_node_for_doc(doc_id, graph_store)
        if node is None:
            continue

        # Deduplicate by node
        if node.id in seen_nodes:
            continue
        seen_nodes.add(node.id)

        # Filter by kind
        if query.include_kinds and node.kind not in query.include_kinds:
            continue

        # Filter by layer
        if query.include_layers and node.layer not in query.include_layers:
            continue

        results.append(ScoredNode(
            node_id=node.id,
            score=score,
            snippet=_build_snippet(node, emb_id),
            match_source="semantic",
        ))

        if len(results) >= query.limit:
            break

    return SemanticQueryResult(
        results=results,
        total_results=len(results),
        embedding_model=embedding_model.model_name,
    )


def _find_node_for_doc(doc_id: str, graph_store: GraphStore):
    """Try to find a GraphNode whose document_id matches."""
    # Try direct lookup with common prefixes
    from kdd.application.extractors.base import KIND_PREFIX

    for prefix in KIND_PREFIX.values():
        node = graph_store.get_node(f"{prefix}:{doc_id}")
        if node is not None:
            return node

    # Fallback: search by ID substring
    return graph_store.get_node(doc_id)


def _build_snippet(node, emb_id: str) -> str:
    title = node.indexed_fields.get("title", "")
    if title:
        return f"[{node.kind.value}] {title}"
    return f"[{node.kind.value}] {node.id}"
