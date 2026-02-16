"""Tests for EventExtractor against real spec files."""

from kdd.application.extractors.kinds.event import EventExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_document


class TestEventExtractor:
    """Parse EVT-KDDDocument-Indexed.md."""

    def setup_method(self):
        self.doc = build_document("specs/01-domain/events/EVT-KDDDocument-Indexed.md")
        self.extractor = EventExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.EVENT

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "Event:EVT-KDDDocument-Indexed"

    def test_node_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields
        assert len(node.indexed_fields["description"]) > 10

    def test_node_has_payload(self):
        node = self.extractor.extract_node(self.doc)
        assert "payload" in node.indexed_fields
        payload = node.indexed_fields["payload"]
        assert isinstance(payload, list)
        assert len(payload) >= 1
        # Payload rows should have Campo column
        field_names = [r.get("Campo", "") for r in payload]
        assert any("document_id" in f for f in field_names)

    def test_node_has_producer(self):
        node = self.extractor.extract_node(self.doc)
        assert "producer" in node.indexed_fields

    def test_node_has_consumers(self):
        node = self.extractor.extract_node(self.doc)
        assert "consumers" in node.indexed_fields

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "Event:EVT-KDDDocument-Indexed"
