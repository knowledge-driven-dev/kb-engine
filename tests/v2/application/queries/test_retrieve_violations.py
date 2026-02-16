"""Tests for QRY-006 RetrieveLayerViolations."""

from kdd.application.queries.retrieve_violations import (
    ViolationsQueryInput,
    retrieve_violations,
)
from kdd.domain.enums import KDDKind, KDDLayer


class TestRetrieveViolations:
    def test_finds_violations(self, graph_store):
        result = retrieve_violations(
            ViolationsQueryInput(),
            graph_store,
        )
        assert result.total_violations == 1
        v = result.violations[0]
        assert v.from_node == "Entity:KDDDocument"
        assert v.to_node == "REQ:REQ-001"
        assert v.from_layer == KDDLayer.DOMAIN
        assert v.to_layer == KDDLayer.VERIFICATION

    def test_violation_rate(self, graph_store):
        result = retrieve_violations(
            ViolationsQueryInput(),
            graph_store,
        )
        assert result.total_edges_analyzed > 0
        assert result.violation_rate > 0
        expected_rate = (1 / result.total_edges_analyzed) * 100
        assert abs(result.violation_rate - round(expected_rate, 2)) < 0.01

    def test_filter_by_kind(self, graph_store):
        result = retrieve_violations(
            ViolationsQueryInput(include_kinds=[KDDKind.ENTITY]),
            graph_store,
        )
        # The violation is from Entity, should still be found
        assert result.total_violations == 1

    def test_filter_excludes_violation(self, graph_store):
        result = retrieve_violations(
            ViolationsQueryInput(include_kinds=[KDDKind.COMMAND]),
            graph_store,
        )
        # The violation is Entity->REQ, filtering by COMMAND excludes it
        assert result.total_violations == 0

    def test_filter_by_layer(self, graph_store):
        result = retrieve_violations(
            ViolationsQueryInput(include_layers=[KDDLayer.DOMAIN]),
            graph_store,
        )
        assert result.total_violations == 1
