"""Tests for NetworkXGraphStore."""

from datetime import datetime

import pytest

from kdd.domain.entities import GraphEdge, GraphNode
from kdd.domain.enums import KDDKind, KDDLayer
from kdd.infrastructure.graph.networkx_store import NetworkXGraphStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _node(id: str, kind: KDDKind = KDDKind.ENTITY, layer: KDDLayer = KDDLayer.DOMAIN, **fields) -> GraphNode:
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
    edge_type: str = "WIKI_LINK",
    violation: bool = False,
) -> GraphEdge:
    return GraphEdge(
        from_node=from_node,
        to_node=to_node,
        edge_type=edge_type,
        source_file="test.md",
        extraction_method="wiki_link",
        layer_violation=violation,
    )


@pytest.fixture
def store():
    return NetworkXGraphStore()


@pytest.fixture
def loaded_store():
    """A store with a small graph:
    Entity:KDDDocument -> BR:BR-DOCUMENT-001 -> UC:UC-001
                       -> CMD:CMD-001 -> UC:UC-001
    Plus a violation edge from Entity -> REQ (lower -> higher)
    """
    s = NetworkXGraphStore()
    nodes = [
        _node("Entity:KDDDocument", KDDKind.ENTITY, KDDLayer.DOMAIN, title="KDDDocument"),
        _node("BR:BR-DOCUMENT-001", KDDKind.BUSINESS_RULE, KDDLayer.DOMAIN, title="Kind Router"),
        _node("CMD:CMD-001", KDDKind.COMMAND, KDDLayer.BEHAVIOR, title="IndexDocument"),
        _node("UC:UC-001", KDDKind.USE_CASE, KDDLayer.BEHAVIOR, title="IndexDocument"),
        _node("REQ:REQ-001", KDDKind.REQUIREMENT, KDDLayer.VERIFICATION, title="Performance"),
    ]
    edges = [
        _edge("Entity:KDDDocument", "BR:BR-DOCUMENT-001", "ENTITY_RULE"),
        _edge("CMD:CMD-001", "Entity:KDDDocument", "WIKI_LINK"),
        _edge("UC:UC-001", "CMD:CMD-001", "UC_EXECUTES_CMD"),
        _edge("UC:UC-001", "BR:BR-DOCUMENT-001", "UC_APPLIES_RULE"),
        _edge("REQ:REQ-001", "UC:UC-001", "REQ_TRACES_TO"),
        # Layer violation: domain -> verification
        _edge("Entity:KDDDocument", "REQ:REQ-001", "WIKI_LINK", violation=True),
    ]
    s.load(nodes, edges)
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoad:
    def test_empty_load(self, store):
        store.load([], [])
        assert store.node_count() == 0
        assert store.edge_count() == 0

    def test_load_nodes_and_edges(self, loaded_store):
        assert loaded_store.node_count() == 5
        assert loaded_store.edge_count() == 6

    def test_reload_clears_previous(self, loaded_store):
        loaded_store.load([], [])
        assert loaded_store.node_count() == 0


class TestGetNode:
    def test_existing_node(self, loaded_store):
        node = loaded_store.get_node("Entity:KDDDocument")
        assert node is not None
        assert node.kind == KDDKind.ENTITY

    def test_missing_node(self, loaded_store):
        assert loaded_store.get_node("Entity:Missing") is None

    def test_has_node(self, loaded_store):
        assert loaded_store.has_node("Entity:KDDDocument")
        assert not loaded_store.has_node("Entity:Missing")


class TestTraverse:
    def test_depth_1_from_entity(self, loaded_store):
        nodes, edges = loaded_store.traverse("Entity:KDDDocument", depth=1)
        node_ids = {n.id for n in nodes}
        assert "Entity:KDDDocument" in node_ids
        assert "BR:BR-DOCUMENT-001" in node_ids
        assert "CMD:CMD-001" in node_ids
        # UC-001 is 2 hops away, should not be found at depth 1
        assert "UC:UC-001" not in node_ids

    def test_depth_2_reaches_further(self, loaded_store):
        nodes, edges = loaded_store.traverse("Entity:KDDDocument", depth=2)
        node_ids = {n.id for n in nodes}
        assert "UC:UC-001" in node_ids

    def test_edge_type_filter(self, loaded_store):
        nodes, edges = loaded_store.traverse(
            "Entity:KDDDocument", depth=2, edge_types=["ENTITY_RULE"]
        )
        node_ids = {n.id for n in nodes}
        assert "BR:BR-DOCUMENT-001" in node_ids
        # CMD-001 connected via WIKI_LINK, should be filtered out
        assert "CMD:CMD-001" not in node_ids

    def test_respect_layers_excludes_violations(self, loaded_store):
        nodes, _ = loaded_store.traverse(
            "Entity:KDDDocument", depth=1, respect_layers=True
        )
        node_ids = {n.id for n in nodes}
        # REQ-001 connected via violation edge, should be excluded
        assert "REQ:REQ-001" not in node_ids

    def test_ignore_layers_includes_violations(self, loaded_store):
        nodes, _ = loaded_store.traverse(
            "Entity:KDDDocument", depth=1, respect_layers=False
        )
        node_ids = {n.id for n in nodes}
        assert "REQ:REQ-001" in node_ids

    def test_unknown_root_returns_empty(self, loaded_store):
        nodes, edges = loaded_store.traverse("Entity:Missing", depth=2)
        assert nodes == []
        assert edges == []


class TestTextSearch:
    def test_search_by_title(self, loaded_store):
        results = loaded_store.text_search("Kind Router")
        assert len(results) == 1
        assert results[0].id == "BR:BR-DOCUMENT-001"

    def test_case_insensitive(self, loaded_store):
        results = loaded_store.text_search("kind router")
        assert len(results) == 1

    def test_search_by_node_id(self, loaded_store):
        results = loaded_store.text_search("CMD-001")
        assert any(n.id == "CMD:CMD-001" for n in results)

    def test_search_no_match(self, loaded_store):
        results = loaded_store.text_search("nonexistent-term-xyz")
        assert len(results) == 0

    def test_search_with_field_filter(self, loaded_store):
        results = loaded_store.text_search("Performance", fields=["title"])
        assert len(results) == 1
        assert results[0].id == "REQ:REQ-001"


class TestNeighbors:
    def test_neighbors_includes_both_directions(self, loaded_store):
        neighbors = loaded_store.neighbors("BR:BR-DOCUMENT-001")
        neighbor_ids = {n.id for n in neighbors}
        # Entity -> BR (outgoing from entity = incoming to BR)
        assert "Entity:KDDDocument" in neighbor_ids
        # UC-001 -> BR (outgoing from UC = incoming to BR)
        assert "UC:UC-001" in neighbor_ids

    def test_missing_node_returns_empty(self, loaded_store):
        assert loaded_store.neighbors("Entity:Missing") == []


class TestEdgeQueries:
    def test_incoming_edges(self, loaded_store):
        incoming = loaded_store.incoming_edges("BR:BR-DOCUMENT-001")
        assert len(incoming) == 2  # Entity->BR and UC->BR
        from_ids = {e.from_node for e in incoming}
        assert "Entity:KDDDocument" in from_ids
        assert "UC:UC-001" in from_ids

    def test_outgoing_edges(self, loaded_store):
        outgoing = loaded_store.outgoing_edges("UC:UC-001")
        assert len(outgoing) == 2  # UC->CMD and UC->BR
        to_ids = {e.to_node for e in outgoing}
        assert "CMD:CMD-001" in to_ids
        assert "BR:BR-DOCUMENT-001" in to_ids

    def test_all_edges(self, loaded_store):
        assert len(loaded_store.all_edges()) == 6

    def test_find_violations(self, loaded_store):
        violations = loaded_store.find_violations()
        assert len(violations) == 1
        assert violations[0].from_node == "Entity:KDDDocument"
        assert violations[0].to_node == "REQ:REQ-001"


class TestReverseTraverse:
    def test_reverse_from_entity(self, loaded_store):
        """CMD-001 references Entity:KDDDocument, so it's a dependent."""
        results = loaded_store.reverse_traverse("Entity:KDDDocument", depth=2)
        dependent_ids = {node.id for node, _ in results}
        assert "CMD:CMD-001" in dependent_ids

    def test_reverse_with_path(self, loaded_store):
        results = loaded_store.reverse_traverse("Entity:KDDDocument", depth=3)
        for node, path in results:
            if node.id == "UC:UC-001":
                # UC-001 -> CMD-001 -> Entity via incoming edges
                assert len(path) >= 1
                break

    def test_reverse_from_leaf(self, loaded_store):
        """REQ-001 has an incoming violation edge from Entity:KDDDocument."""
        results = loaded_store.reverse_traverse("REQ:REQ-001", depth=2)
        dependent_ids = {node.id for node, _ in results}
        assert "Entity:KDDDocument" in dependent_ids

    def test_reverse_missing_node(self, loaded_store):
        results = loaded_store.reverse_traverse("Entity:Missing", depth=2)
        assert results == []
