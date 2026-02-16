"""Tests for the kdd REST API server."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from kdd.api.server import app, _get_container
from kdd.domain.entities import GraphEdge, GraphNode, IndexManifest, IndexStats
from kdd.domain.enums import EdgeType, IndexLevel, KDDKind, KDDLayer
from kdd.infrastructure.graph.networkx_store import NetworkXGraphStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _node(id: str, kind: KDDKind, layer: KDDLayer, **fields) -> GraphNode:
    return GraphNode(
        id=id, kind=kind, source_file=f"{id}.md", source_hash="abc",
        layer=layer, indexed_fields=fields,
    )


def _edge(from_node: str, to_node: str, edge_type: str, violation: bool = False) -> GraphEdge:
    return GraphEdge(
        from_node=from_node, to_node=to_node, edge_type=edge_type,
        source_file="test.md", extraction_method="section_content",
        layer_violation=violation,
    )


NODES = [
    _node("Entity:A", KDDKind.ENTITY, KDDLayer.DOMAIN, title="Entity A"),
    _node("Entity:B", KDDKind.ENTITY, KDDLayer.DOMAIN, title="Entity B"),
    _node("CMD:C1", KDDKind.COMMAND, KDDLayer.BEHAVIOR, title="Command C1"),
    _node("REQ:R1", KDDKind.REQUIREMENT, KDDLayer.VERIFICATION, title="Requirement R1"),
]

EDGES = [
    _edge("Entity:A", "Entity:B", EdgeType.DOMAIN_RELATION.value),
    _edge("CMD:C1", "Entity:A", EdgeType.WIKI_LINK.value),
    _edge("Entity:A", "REQ:R1", EdgeType.WIKI_LINK.value, violation=True),
]


class FakeContainer:
    """Minimal container for API tests."""

    def __init__(self):
        self.graph_store = NetworkXGraphStore()
        self.graph_store.load(NODES, EDGES)
        self.vector_store = None
        self.embedding_model = None

    def ensure_loaded(self):
        return True


@pytest.fixture
def client():
    container = FakeContainer()
    app.dependency_overrides[_get_container] = lambda: container
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestContextEndpoint:
    """POST /v1/retrieve/context — QRY-003 hybrid search."""

    def test_context_search(self, client):
        resp = client.post("/v1/retrieve/context", json={
            "query_text": "Entity A",
            "min_score": 0.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total_results" in data
        # L1 index → no semantic, should get lexical + graph results
        assert any("NO_EMBEDDINGS" in w for w in data["warnings"])

    def test_context_short_query(self, client):
        resp = client.post("/v1/retrieve/context", json={"query_text": "ab"})
        assert resp.status_code == 422  # pydantic validation: min_length=3


class TestGraphEndpoint:
    """GET /v1/retrieve/graph — QRY-001 traversal."""

    def test_graph_traversal(self, client):
        resp = client.get("/v1/retrieve/graph", params={"node_id": "Entity:A"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["center_node"] == "Entity:A"
        assert data["total_nodes"] > 1

    def test_graph_not_found(self, client):
        resp = client.get("/v1/retrieve/graph", params={"node_id": "Entity:MISSING"})
        assert resp.status_code == 404


class TestImpactEndpoint:
    """GET /v1/retrieve/impact — QRY-004."""

    def test_impact_analysis(self, client):
        resp = client.get("/v1/retrieve/impact", params={"node_id": "Entity:A"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["analyzed_node"] == "Entity:A"
        assert isinstance(data["directly_affected"], list)

    def test_impact_not_found(self, client):
        resp = client.get("/v1/retrieve/impact", params={"node_id": "NOPE"})
        assert resp.status_code == 404


class TestCoverageEndpoint:
    """GET /v1/retrieve/coverage — QRY-005."""

    def test_coverage(self, client):
        resp = client.get("/v1/retrieve/coverage", params={"node_id": "Entity:A"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_id"] == "Entity:A"
        assert "coverage_percent" in data
        assert isinstance(data["categories"], list)

    def test_coverage_not_found(self, client):
        resp = client.get("/v1/retrieve/coverage", params={"node_id": "NOPE"})
        assert resp.status_code == 404


class TestViolationsEndpoint:
    """GET /v1/retrieve/layer-violations — QRY-006."""

    def test_violations_list(self, client):
        resp = client.get("/v1/retrieve/layer-violations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_violations"] >= 1
        assert data["total_edges_analyzed"] >= 1
        assert len(data["violations"]) >= 1
        # Verify the known violation
        v = data["violations"][0]
        assert "from_node" in v
        assert "from_layer" in v


class TestSearchEndpoint:
    """POST /v1/retrieve/search — QRY-002 semantic. Requires L2."""

    def test_search_requires_l2(self, client):
        resp = client.post("/v1/retrieve/search", json={"query_text": "test query"})
        assert resp.status_code == 400
        assert "L2" in resp.json()["detail"]


class TestNoContainerLoaded:
    """When no container is set."""

    def test_503_without_container(self):
        app.dependency_overrides.clear()
        # Reset app state
        if hasattr(app.state, "container"):
            del app.state.container

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/retrieve/layer-violations")
        assert resp.status_code == 503
