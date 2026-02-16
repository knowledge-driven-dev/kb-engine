"""Tests for RequirementExtractor against real spec files."""

from kdd.application.extractors.kinds.requirement import RequirementExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestRequirementExtractor:
    """Parse REQ-001-Performance.md."""

    def setup_method(self):
        self.doc = build_document("specs/04-verification/criteria/REQ-001-Performance.md")
        self.extractor = RequirementExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.REQUIREMENT

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "REQ:REQ-001"

    def test_node_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields
        assert len(node.indexed_fields["description"]) > 10

    def test_node_has_acceptance_criteria(self):
        node = self.extractor.extract_node(self.doc)
        assert "acceptance_criteria" in node.indexed_fields
        assert "CA-1" in node.indexed_fields["acceptance_criteria"]

    def test_node_has_traceability(self):
        node = self.extractor.extract_node(self.doc)
        assert "traceability" in node.indexed_fields
        assert "UC-001" in node.indexed_fields["traceability"]

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "REQ:REQ-001"
