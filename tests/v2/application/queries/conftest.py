"""Shared fixtures for query tests.

Provides a pre-built graph store and vector store with a representative
KDD knowledge graph.
"""

from datetime import datetime

import pytest

from kdd.domain.entities import Embedding, GraphEdge, GraphNode
from kdd.domain.enums import EdgeType, KDDKind, KDDLayer
from kdd.infrastructure.graph.networkx_store import NetworkXGraphStore
from kdd.infrastructure.vector.hnswlib_store import HNSWLibVectorStore


def _node(
    id: str,
    kind: KDDKind,
    layer: KDDLayer,
    **fields,
) -> GraphNode:
    return GraphNode(
        id=id,
        kind=kind,
        source_file=f"{id}.md",
        source_hash="abc123",
        layer=layer,
        indexed_fields=fields,
    )


def _edge(
    from_node: str,
    to_node: str,
    edge_type: str,
    violation: bool = False,
) -> GraphEdge:
    return GraphEdge(
        from_node=from_node,
        to_node=to_node,
        edge_type=edge_type,
        source_file="test.md",
        extraction_method="section_content",
        layer_violation=violation,
    )


# A representative mini-graph of the KB Engine specs
NODES = [
    _node("Entity:KDDDocument", KDDKind.ENTITY, KDDLayer.DOMAIN,
          title="KDDDocument", description="Atomic input unit"),
    _node("Entity:GraphNode", KDDKind.ENTITY, KDDLayer.DOMAIN,
          title="GraphNode", description="Node in the knowledge graph"),
    _node("BR:BR-DOCUMENT-001", KDDKind.BUSINESS_RULE, KDDLayer.DOMAIN,
          title="Kind Router", description="Routes documents to extractors"),
    _node("BR:BR-LAYER-001", KDDKind.BUSINESS_RULE, KDDLayer.DOMAIN,
          title="Layer Validation", description="Validates layer dependencies"),
    _node("CMD:CMD-001", KDDKind.COMMAND, KDDLayer.BEHAVIOR,
          title="IndexDocument", description="Index a single document"),
    _node("CMD:CMD-002", KDDKind.COMMAND, KDDLayer.BEHAVIOR,
          title="IndexIncremental", description="Incremental re-indexing"),
    _node("UC:UC-001", KDDKind.USE_CASE, KDDLayer.BEHAVIOR,
          title="IndexDocument", description="Full indexing flow"),
    _node("UC:UC-004", KDDKind.USE_CASE, KDDLayer.BEHAVIOR,
          title="RetrieveContext", description="Hybrid search for agents"),
    _node("QRY:QRY-003", KDDKind.QUERY, KDDLayer.BEHAVIOR,
          title="RetrieveHybrid", description="Fusion search"),
    _node("REQ:REQ-001", KDDKind.REQUIREMENT, KDDLayer.VERIFICATION,
          title="Performance", description="Performance requirements"),
]

EDGES = [
    # Entity relationships
    _edge("Entity:KDDDocument", "BR:BR-DOCUMENT-001", EdgeType.ENTITY_RULE.value),
    _edge("Entity:KDDDocument", "BR:BR-LAYER-001", EdgeType.ENTITY_RULE.value),
    _edge("Entity:KDDDocument", "Entity:GraphNode", EdgeType.DOMAIN_RELATION.value),
    # Command relationships
    _edge("CMD:CMD-001", "Entity:KDDDocument", EdgeType.WIKI_LINK.value),
    _edge("CMD:CMD-002", "CMD:CMD-001", EdgeType.WIKI_LINK.value),
    # UC relationships
    _edge("UC:UC-001", "CMD:CMD-001", EdgeType.UC_EXECUTES_CMD.value),
    _edge("UC:UC-001", "BR:BR-DOCUMENT-001", EdgeType.UC_APPLIES_RULE.value),
    _edge("UC:UC-001", "BR:BR-LAYER-001", EdgeType.UC_APPLIES_RULE.value),
    _edge("UC:UC-004", "QRY:QRY-003", EdgeType.UC_EXECUTES_CMD.value),
    # Requirement traceability
    _edge("REQ:REQ-001", "UC:UC-001", EdgeType.REQ_TRACES_TO.value),
    _edge("REQ:REQ-001", "UC:UC-004", EdgeType.REQ_TRACES_TO.value),
    # Layer violation: domain entity references verification requirement
    _edge("Entity:KDDDocument", "REQ:REQ-001", EdgeType.WIKI_LINK.value, violation=True),
]


@pytest.fixture
def graph_store():
    """A NetworkX graph store loaded with the mini KB Engine graph."""
    store = NetworkXGraphStore()
    store.load(NODES, EDGES)
    return store


@pytest.fixture
def vector_store():
    """A vector store with embeddings for some of the nodes."""
    store = HNSWLibVectorStore()
    dim = 8

    embeddings = [
        _emb("KDDDocument:chunk-0", "KDDDocument", KDDKind.ENTITY,
             _make_vec(dim, [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])),
        _emb("BR-DOCUMENT-001:chunk-0", "BR-DOCUMENT-001", KDDKind.BUSINESS_RULE,
             _make_vec(dim, [0.8, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])),
        _emb("CMD-001:chunk-0", "CMD-001", KDDKind.COMMAND,
             _make_vec(dim, [0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0])),
        _emb("UC-001:chunk-0", "UC-001", KDDKind.USE_CASE,
             _make_vec(dim, [0.3, 0.3, 0.3, 0.5, 0.0, 0.0, 0.0, 0.0])),
        _emb("QRY-003:chunk-0", "QRY-003", KDDKind.QUERY,
             _make_vec(dim, [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])),
        _emb("REQ-001:chunk-0", "REQ-001", KDDKind.REQUIREMENT,
             _make_vec(dim, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])),
    ]
    store.load(embeddings)
    return store


def _make_vec(dim: int, values: list[float]) -> list[float]:
    """Ensure vector has exactly *dim* dimensions."""
    return (values + [0.0] * dim)[:dim]


def _emb(id: str, doc_id: str, kind: KDDKind, vector: list[float]) -> Embedding:
    return Embedding(
        id=id,
        document_id=doc_id,
        document_kind=kind,
        section_path="Descripción",
        chunk_index=0,
        raw_text="test",
        context_text="test context",
        vector=vector,
        model="test-model",
        dimensions=len(vector),
        text_hash="hash",
        generated_at=datetime.now(),
    )
