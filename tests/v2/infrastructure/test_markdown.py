"""Tests for kdd.infrastructure.parsing.markdown."""

from kdd.infrastructure.parsing.markdown import (
    extract_frontmatter,
    extract_snippet,
    heading_to_anchor,
    parse_markdown_sections,
)


class TestExtractFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nkind: entity\naliases: [Orden]\n---\n\n# Pedido\n\nBody."
        meta, body = extract_frontmatter(content)
        assert meta["kind"] == "entity"
        assert meta["aliases"] == ["Orden"]
        assert body.strip().startswith("# Pedido")

    def test_no_frontmatter(self):
        content = "# Just a heading\n\nSome text."
        meta, body = extract_frontmatter(content)
        assert meta == {}
        assert "Just a heading" in body

    def test_empty_string(self):
        meta, body = extract_frontmatter("")
        assert meta == {}
        assert body == ""

    def test_invalid_yaml(self):
        content = "---\n: bad: yaml: here\n---\nBody"
        meta, body = extract_frontmatter(content)
        # Should not crash — returns something (depends on frontmatter lib)
        assert isinstance(meta, dict)


class TestParseMarkdownSections:
    def test_single_section(self):
        content = "# Title\n\nParagraph one.\n\nParagraph two."
        sections = parse_markdown_sections(content)
        assert len(sections) == 1
        assert sections[0].heading == "Title"
        assert sections[0].level == 1
        assert "Paragraph one." in sections[0].content

    def test_nested_sections(self):
        content = (
            "# Top\n\nIntro.\n\n"
            "## Child\n\nChild text.\n\n"
            "### Grandchild\n\nDeep text."
        )
        sections = parse_markdown_sections(content)
        assert len(sections) == 3
        assert sections[0].heading == "Top"
        assert sections[1].heading == "Child"
        assert sections[2].heading == "Grandchild"
        # Path should be hierarchical
        assert sections[2].path == "top.child.grandchild"

    def test_sibling_sections(self):
        content = "## A\n\nText A.\n\n## B\n\nText B."
        sections = parse_markdown_sections(content)
        assert len(sections) == 2
        assert sections[0].heading == "A"
        assert sections[1].heading == "B"
        # Siblings should have independent paths
        assert sections[0].path == "a"
        assert sections[1].path == "b"

    def test_empty_content(self):
        sections = parse_markdown_sections("")
        assert sections == []

    def test_content_without_headings(self):
        sections = parse_markdown_sections("Just some text without headings.")
        assert sections == []

    def test_heading_with_special_chars(self):
        content = "## Descripción (v2)\n\nContent."
        sections = parse_markdown_sections(content)
        assert sections[0].heading == "Descripción (v2)"

    def test_real_entity_structure(self):
        content = (
            "## Descripción\n\nEntity description.\n\n"
            "## Atributos\n\n| Name | Type |\n|---|---|\n| id | uuid |\n\n"
            "## Relaciones\n\nRelation info.\n\n"
            "## Invariantes\n\n- Invariant 1."
        )
        sections = parse_markdown_sections(content)
        assert len(sections) == 4
        headings = [s.heading for s in sections]
        assert headings == ["Descripción", "Atributos", "Relaciones", "Invariantes"]


class TestHeadingToAnchor:
    def test_simple(self):
        assert heading_to_anchor("Atributos") == "atributos"

    def test_spaces(self):
        assert heading_to_anchor("Ciclo de Vida") == "ciclo-de-vida"

    def test_special_chars(self):
        assert heading_to_anchor("Entity: User") == "entity-user"

    def test_parentheses(self):
        assert heading_to_anchor("Estados (v2)") == "estados-v2"

    def test_accented(self):
        assert heading_to_anchor("Descripción") == "descripcion"


class TestExtractSnippet:
    def test_short_content(self):
        assert extract_snippet("Hello world.") == "Hello world."

    def test_truncation_at_sentence(self):
        # ". " must be past the halfway mark of max_length for sentence truncation
        text = "This is a fairly long first sentence. " + "A" * 200
        snippet = extract_snippet(text, max_length=60)
        assert snippet == "This is a fairly long first sentence."

    def test_truncation_at_word(self):
        text = "word " * 100
        snippet = extract_snippet(text, max_length=50)
        assert snippet.endswith("...")
        assert len(snippet) <= 55  # some margin for "..."

    def test_strips_markdown(self):
        text = "**Bold** and *italic* and [link](http://x.com)"
        snippet = extract_snippet(text)
        assert "**" not in snippet
        assert "*" not in snippet
        assert "http" not in snippet
        assert "Bold" in snippet
        assert "link" in snippet
