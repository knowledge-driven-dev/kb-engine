"""Tests for CommandExtractor against real spec files."""

from kdd.application.extractors.kinds.command import CommandExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestCommandExtractor:
    """Parse CMD-001-IndexDocument.md."""

    def setup_method(self):
        self.doc = build_document("specs/02-behavior/commands/CMD-001-IndexDocument.md")
        self.extractor = CommandExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.COMMAND

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "CMD:CMD-001"

    def test_node_has_purpose(self):
        node = self.extractor.extract_node(self.doc)
        assert "purpose" in node.indexed_fields
        assert len(node.indexed_fields["purpose"]) > 10

    def test_node_has_input_params(self):
        node = self.extractor.extract_node(self.doc)
        params = node.indexed_fields.get("input_params", [])
        assert len(params) >= 2  # source_path, index_path, force

    def test_node_has_preconditions(self):
        node = self.extractor.extract_node(self.doc)
        assert "preconditions" in node.indexed_fields

    def test_node_has_postconditions(self):
        node = self.extractor.extract_node(self.doc)
        assert "postconditions" in node.indexed_fields

    def test_node_has_errors(self):
        node = self.extractor.extract_node(self.doc)
        errors = node.indexed_fields.get("errors", [])
        assert len(errors) >= 1

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_include_emits(self):
        edges = self.extractor.extract_edges(self.doc)
        emits = [e for e in edges if e.edge_type == "EMITS"]
        # CMD-001 postconditions reference EVT-KDDDocument-Detected, etc.
        assert len(emits) >= 1

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "CMD:CMD-001"
