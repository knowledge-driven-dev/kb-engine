"""Tests for QueryExtractor against real spec files."""

from kdd.application.extractors.kinds.query import QueryExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestQueryExtractor:
    """Parse QRY-001-RetrieveByGraph.md."""

    def setup_method(self):
        self.doc = build_document("specs/02-behavior/queries/QRY-001-RetrieveByGraph.md")
        self.extractor = QueryExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.QUERY

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "QRY:QRY-001"

    def test_node_has_purpose(self):
        node = self.extractor.extract_node(self.doc)
        assert "purpose" in node.indexed_fields
        assert len(node.indexed_fields["purpose"]) > 10

    def test_node_has_input_params(self):
        node = self.extractor.extract_node(self.doc)
        params = node.indexed_fields.get("input_params", [])
        assert len(params) >= 1  # root_node, depth, etc.

    def test_node_has_output(self):
        node = self.extractor.extract_node(self.doc)
        assert "output_structure" in node.indexed_fields

    def test_node_has_errors(self):
        node = self.extractor.extract_node(self.doc)
        errors = node.indexed_fields.get("errors", [])
        assert len(errors) >= 1

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "QRY:QRY-001"
