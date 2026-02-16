"""Tests for kdd.infrastructure.parsing.wiki_links."""

from kdd.infrastructure.parsing.wiki_links import (
    WikiLink,
    extract_wiki_link_targets,
    extract_wiki_links,
)


class TestExtractWikiLinks:
    def test_simple_link(self):
        links = extract_wiki_links("See [[KDDDocument]] for details.")
        assert len(links) == 1
        assert links[0].target == "KDDDocument"
        assert links[0].domain is None
        assert links[0].alias is None

    def test_multiple_links(self):
        content = "The [[KDDDocument]] produces a [[GraphNode]] and [[GraphEdge|edges]]."
        links = extract_wiki_links(content)
        assert len(links) == 3
        targets = [l.target for l in links]
        assert "KDDDocument" in targets
        assert "GraphNode" in targets
        assert "GraphEdge" in targets

    def test_cross_domain_link(self):
        links = extract_wiki_links("References [[auth::Usuario]] entity.")
        assert len(links) == 1
        assert links[0].target == "Usuario"
        assert links[0].domain == "auth"
        assert links[0].alias is None

    def test_alias_link(self):
        links = extract_wiki_links("The [[GraphEdge|edges]] connect nodes.")
        assert len(links) == 1
        assert links[0].target == "GraphEdge"
        assert links[0].alias == "edges"
        assert links[0].domain is None

    def test_cross_domain_with_alias(self):
        links = extract_wiki_links("See [[payments::Pedido|order]].")
        assert len(links) == 1
        assert links[0].target == "Pedido"
        assert links[0].domain == "payments"
        assert links[0].alias == "order"

    def test_no_links(self):
        links = extract_wiki_links("No links here, just [markdown](http://x.com).")
        assert links == []

    def test_empty_brackets(self):
        links = extract_wiki_links("Empty [[ ]] should be skipped.")
        assert links == []

    def test_multiline(self):
        content = "Line one [[A]].\nLine two [[B]].\nLine three [[C]]."
        links = extract_wiki_links(content)
        assert len(links) == 3

    def test_event_reference(self):
        links = extract_wiki_links("Emits [[EVT-Pedido-Confirmado]].")
        assert links[0].target == "EVT-Pedido-Confirmado"

    def test_spec_id_reference(self):
        links = extract_wiki_links("See [[BR-DOCUMENT-001]] and [[UC-001-IndexDocument]].")
        assert len(links) == 2
        targets = [l.target for l in links]
        assert "BR-DOCUMENT-001" in targets
        assert "UC-001-IndexDocument" in targets

    def test_frozen(self):
        links = extract_wiki_links("[[A]]")
        import dataclasses
        assert dataclasses.is_dataclass(links[0])


class TestExtractWikiLinkTargets:
    def test_returns_flat_list(self):
        targets = extract_wiki_link_targets("[[A]] and [[B|alias]] and [[d::C]]")
        assert targets == ["A", "B", "C"]
