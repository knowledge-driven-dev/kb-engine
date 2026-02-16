"""Tests for QRY-001 RetrieveByGraph."""

import pytest

from kdd.application.queries.retrieve_graph import (
    GraphQueryInput,
    retrieve_by_graph,
)


class TestRetrieveByGraph:
    def test_basic_traversal(self, graph_store):
        result = retrieve_by_graph(
            GraphQueryInput(root_node="Entity:KDDDocument", depth=1),
            graph_store,
        )
        assert result.center_node is not None
        assert result.center_node.id == "Entity:KDDDocument"
        node_ids = {s.node_id for s in result.related_nodes}
        assert "BR:BR-DOCUMENT-001" in node_ids
        assert "CMD:CMD-001" in node_ids

    def test_depth_2_reaches_uc(self, graph_store):
        result = retrieve_by_graph(
            GraphQueryInput(root_node="Entity:KDDDocument", depth=2),
            graph_store,
        )
        node_ids = {s.node_id for s in result.related_nodes}
        assert "UC:UC-001" in node_ids

    def test_edge_type_filter(self, graph_store):
        result = retrieve_by_graph(
            GraphQueryInput(
                root_node="Entity:KDDDocument",
                depth=2,
                edge_types=["ENTITY_RULE"],
            ),
            graph_store,
        )
        node_ids = {s.node_id for s in result.related_nodes}
        assert "BR:BR-DOCUMENT-001" in node_ids
        assert "CMD:CMD-001" not in node_ids

    def test_kind_filter(self, graph_store):
        from kdd.domain.enums import KDDKind
        result = retrieve_by_graph(
            GraphQueryInput(
                root_node="Entity:KDDDocument",
                depth=2,
                include_kinds=[KDDKind.BUSINESS_RULE],
            ),
            graph_store,
        )
        assert all(
            graph_store.get_node(s.node_id).kind == KDDKind.BUSINESS_RULE
            for s in result.related_nodes
        )

    def test_scores_descending(self, graph_store):
        result = retrieve_by_graph(
            GraphQueryInput(root_node="Entity:KDDDocument", depth=3),
            graph_store,
        )
        scores = [s.score for s in result.related_nodes]
        assert scores == sorted(scores, reverse=True)

    def test_node_not_found(self, graph_store):
        with pytest.raises(ValueError, match="NODE_NOT_FOUND"):
            retrieve_by_graph(
                GraphQueryInput(root_node="Entity:Missing"),
                graph_store,
            )

    def test_edges_returned(self, graph_store):
        result = retrieve_by_graph(
            GraphQueryInput(root_node="Entity:KDDDocument", depth=1),
            graph_store,
        )
        assert result.total_edges > 0
        assert len(result.edges) == result.total_edges
