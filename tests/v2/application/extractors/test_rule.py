"""Tests for RuleExtractor against real spec files."""

from kdd.application.extractors.kinds.business_rule import RuleExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestRuleExtractor:
    """Parse BR-DOCUMENT-001.md."""

    def setup_method(self):
        self.doc = build_document("specs/01-domain/rules/BR-DOCUMENT-001.md")
        self.extractor = RuleExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.BUSINESS_RULE

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "BR:BR-DOCUMENT-001"

    def test_node_has_declaration(self):
        node = self.extractor.extract_node(self.doc)
        assert "declaration" in node.indexed_fields
        assert len(node.indexed_fields["declaration"]) > 10

    def test_node_has_when_applies(self):
        node = self.extractor.extract_node(self.doc)
        assert "when_applies" in node.indexed_fields

    def test_node_has_violation(self):
        node = self.extractor.extract_node(self.doc)
        assert "violation" in node.indexed_fields

    def test_node_has_examples(self):
        node = self.extractor.extract_node(self.doc)
        assert "examples" in node.indexed_fields

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_include_entity_rule(self):
        edges = self.extractor.extract_edges(self.doc)
        entity_rules = [e for e in edges if e.edge_type == "ENTITY_RULE"]
        # BR-DOCUMENT-001 declaration references KDDDocument
        assert len(entity_rules) >= 1
        targets = {e.to_node for e in entity_rules}
        assert any("KDDDocument" in t for t in targets)

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "BR:BR-DOCUMENT-001"
