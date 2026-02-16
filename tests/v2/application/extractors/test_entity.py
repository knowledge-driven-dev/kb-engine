"""Tests for EntityExtractor against real spec files.

Validates BDD: index-entity.feature SCN-001 (node + edges for entity).
"""

from kdd.application.extractors.kinds.entity import EntityExtractor
from kdd.domain.enums import KDDKind, KDDLayer

from .conftest import build_document


class TestEntityExtractor:
    """Parse real entity spec: KDDDocument.md."""

    def setup_method(self):
        self.doc = build_document("specs/01-domain/entities/KDDDocument.md")
        self.extractor = EntityExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.ENTITY

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "Entity:KDDDocument"

    def test_node_kind_and_layer(self):
        node = self.extractor.extract_node(self.doc)
        assert node.kind == KDDKind.ENTITY
        assert node.layer == KDDLayer.DOMAIN

    def test_node_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields
        assert len(node.indexed_fields["description"]) > 10

    def test_node_has_attributes(self):
        node = self.extractor.extract_node(self.doc)
        attrs = node.indexed_fields.get("attributes", [])
        assert len(attrs) > 0
        # KDDDocument has id, kind, source_path, etc.
        attr_names = {a.get("Atributo", a.get("Attribute", "")) for a in attrs}
        assert "`id`" in attr_names or "id" in attr_names

    def test_node_has_relations(self):
        node = self.extractor.extract_node(self.doc)
        rels = node.indexed_fields.get("relations", [])
        assert len(rels) > 0

    def test_node_has_invariants(self):
        node = self.extractor.extract_node(self.doc)
        invs = node.indexed_fields.get("invariants", [])
        assert len(invs) > 0

    def test_node_has_lifecycle(self):
        node = self.extractor.extract_node(self.doc)
        assert "state_machine" in node.indexed_fields

    def test_node_status_from_frontmatter(self):
        node = self.extractor.extract_node(self.doc)
        assert node.status == "draft"

    def test_node_aliases_from_frontmatter(self):
        node = self.extractor.extract_node(self.doc)
        assert "Document" in node.aliases or "Spec" in node.aliases

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_include_domain_relations(self):
        edges = self.extractor.extract_edges(self.doc)
        domain_rels = [e for e in edges if e.edge_type == "DOMAIN_RELATION"]
        # KDDDocument has relations to GraphNode, GraphEdge, Embedding, IndexManifest
        assert len(domain_rels) >= 1

    def test_edges_have_correct_source(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "Entity:KDDDocument"
            assert edge.source_file == self.doc.source_path

    def test_edges_include_emits(self):
        edges = self.extractor.extract_edges(self.doc)
        emits = [e for e in edges if e.edge_type == "EMITS"]
        # KDDDocument lifecycle has EVT-KDDDocument-Detected, etc.
        assert len(emits) >= 1
        for e in emits:
            assert e.to_node.startswith("Event:")

    def test_no_duplicate_edges(self):
        edges = self.extractor.extract_edges(self.doc)
        keys = [(e.from_node, e.to_node, e.edge_type) for e in edges]
        assert len(keys) == len(set(keys))


class TestEntityExtractorGraphNode:
    """Parse GraphNode.md — simpler entity with fewer sections."""

    def setup_method(self):
        self.doc = build_document("specs/01-domain/entities/GraphNode.md")
        self.extractor = EntityExtractor()

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "Entity:GraphNode"

    def test_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields

    def test_has_attributes(self):
        node = self.extractor.extract_node(self.doc)
        assert len(node.indexed_fields.get("attributes", [])) > 0
