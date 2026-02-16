"""Tests for UseCaseExtractor against real spec files."""

from kdd.application.extractors.kinds.use_case import UseCaseExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestUseCaseExtractor:
    """Parse UC-001-IndexDocument.md."""

    def setup_method(self):
        self.doc = build_document("specs/02-behavior/use-cases/UC-001-IndexDocument.md")
        self.extractor = UseCaseExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.USE_CASE

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "UC:UC-001"

    def test_node_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields
        assert len(node.indexed_fields["description"]) > 10

    def test_node_has_actors(self):
        node = self.extractor.extract_node(self.doc)
        assert "actors" in node.indexed_fields
        assert "Developer" in node.indexed_fields["actors"]

    def test_node_has_main_flow(self):
        node = self.extractor.extract_node(self.doc)
        assert "main_flow" in node.indexed_fields

    def test_node_has_preconditions(self):
        node = self.extractor.extract_node(self.doc)
        assert "preconditions" in node.indexed_fields

    def test_node_has_postconditions(self):
        node = self.extractor.extract_node(self.doc)
        assert "postconditions" in node.indexed_fields

    def test_node_has_alternatives(self):
        node = self.extractor.extract_node(self.doc)
        # Alternatives may be in sub-sections (### FA-1, FA-2, etc.)
        # so the H2 "Flujos Alternativos" itself may have no content.
        # The extractor collects sub-sections as well.
        assert "alternatives" in node.indexed_fields

    def test_node_has_exceptions(self):
        node = self.extractor.extract_node(self.doc)
        # Same: exceptions live in sub-sections (### EX-1, etc.)
        assert "exceptions" in node.indexed_fields

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_include_uc_applies_rule(self):
        edges = self.extractor.extract_edges(self.doc)
        rule_edges = [e for e in edges if e.edge_type == "UC_APPLIES_RULE"]
        # UC-001 references BR-DOCUMENT-001, BR-EMBEDDING-001, etc.
        assert len(rule_edges) >= 1
        # Targets should be BR:, BP:, or XP:
        for e in rule_edges:
            assert e.to_node.startswith(("BR:", "BP:", "XP:"))

    def test_edges_include_uc_executes_cmd(self):
        edges = self.extractor.extract_edges(self.doc)
        cmd_edges = [e for e in edges if e.edge_type == "UC_EXECUTES_CMD"]
        # UC-001 references CMD-001-IndexDocument
        assert len(cmd_edges) >= 1
        for e in cmd_edges:
            assert e.to_node.startswith("CMD:")

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "UC:UC-001"
