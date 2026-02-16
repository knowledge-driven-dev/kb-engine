"""Tests for PRDExtractor against real spec files."""

from kdd.application.extractors.kinds.prd import PRDExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestPRDExtractor:
    """Parse PRD-KBEngine.md."""

    def setup_method(self):
        self.doc = build_document("specs/00-requirements/PRD-KBEngine.md")
        self.extractor = PRDExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.PRD

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "PRD:PRD-KBEngine"

    def test_node_has_problem(self):
        node = self.extractor.extract_node(self.doc)
        assert "problem" in node.indexed_fields
        assert len(node.indexed_fields["problem"]) > 20

    def test_node_has_scope(self):
        node = self.extractor.extract_node(self.doc)
        assert "scope" in node.indexed_fields
        assert "alcance" in node.indexed_fields["scope"].lower() or \
               "v1" in node.indexed_fields["scope"].lower()

    def test_node_has_users(self):
        node = self.extractor.extract_node(self.doc)
        assert "users" in node.indexed_fields

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "PRD:PRD-KBEngine"
