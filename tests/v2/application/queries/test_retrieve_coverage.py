"""Tests for QRY-005 RetrieveCoverage."""

import pytest

from kdd.application.queries.retrieve_coverage import (
    CoverageQueryInput,
    retrieve_coverage,
)


class TestRetrieveCoverage:
    def test_entity_coverage(self, graph_store):
        """Entity:KDDDocument has business rules connected."""
        result = retrieve_coverage(
            CoverageQueryInput(node_id="Entity:KDDDocument"),
            graph_store,
        )
        assert result.analyzed_node is not None
        assert result.analyzed_node.id == "Entity:KDDDocument"

        # Should have categories defined for entities
        cat_names = {c.name for c in result.categories}
        assert "business_rules" in cat_names

        # business_rules should be covered (BR-DOCUMENT-001, BR-LAYER-001)
        br_cat = next(c for c in result.categories if c.name == "business_rules")
        assert br_cat.status == "covered"
        assert len(br_cat.found) >= 1

    def test_coverage_percentage(self, graph_store):
        result = retrieve_coverage(
            CoverageQueryInput(node_id="Entity:KDDDocument"),
            graph_store,
        )
        assert 0 <= result.coverage_percent <= 100
        assert result.present + result.missing == len(result.categories)

    def test_uc_coverage(self, graph_store):
        """UC-001 has commands and rules connected."""
        result = retrieve_coverage(
            CoverageQueryInput(node_id="UC:UC-001"),
            graph_store,
        )
        cat_names = {c.name for c in result.categories}
        assert "commands" in cat_names
        assert "rules" in cat_names

    def test_node_not_found(self, graph_store):
        with pytest.raises(ValueError, match="NODE_NOT_FOUND"):
            retrieve_coverage(
                CoverageQueryInput(node_id="Entity:Missing"),
                graph_store,
            )

    def test_unknown_kind_no_rules(self, graph_store):
        """QRY:QRY-003 is a query kind — no coverage rules defined."""
        with pytest.raises(ValueError, match="UNKNOWN_KIND"):
            retrieve_coverage(
                CoverageQueryInput(node_id="QRY:QRY-003"),
                graph_store,
            )
