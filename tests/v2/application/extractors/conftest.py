"""Shared fixtures for extractor tests.

Provides helpers that build a KDDDocument from a real spec file on disk
or from synthetic markdown content, so extractors can be tested against
actual project specs or fabricated examples.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kdd.domain.entities import KDDDocument
from kdd.domain.enums import KDDKind, KDDLayer
from kdd.domain.rules import detect_layer, route_document
from kdd.infrastructure.parsing.hashing import compute_content_hash
from kdd.infrastructure.parsing.markdown import extract_frontmatter, parse_markdown_sections
from kdd.infrastructure.parsing.wiki_links import extract_wiki_link_targets

# Root of the specs/ directory in this project
SPECS_ROOT = Path(__file__).resolve().parents[4] / "specs"


def build_synthetic_document(
    content: str,
    *,
    spec_path: str | None = None,
) -> KDDDocument:
    """Build a KDDDocument from synthetic markdown content.

    Useful for kinds that don't have real spec files yet.
    The content must include YAML front-matter with at least ``id`` and ``kind``.
    """
    fm, body = extract_frontmatter(content)
    assert "kind" in fm, "Synthetic content must have 'kind' in front-matter"
    assert "id" in fm, "Synthetic content must have 'id' in front-matter"

    if spec_path is None:
        spec_path = f"specs/synthetic/{fm['id']}.md"

    route = route_document(fm, spec_path)
    assert route.kind is not None, f"Could not route kind '{fm['kind']}'"

    sections = parse_markdown_sections(body)
    wiki_links = extract_wiki_link_targets(body)
    layer = detect_layer(spec_path) or KDDLayer.DOMAIN

    return KDDDocument(
        id=fm["id"],
        kind=route.kind,
        source_path=spec_path,
        source_hash=compute_content_hash(content),
        layer=layer,
        front_matter=fm,
        sections=sections,
        wiki_links=wiki_links,
    )


def build_document(spec_path: str) -> KDDDocument:
    """Build a KDDDocument from a real spec file path (relative to repo root).

    Example: ``build_document("specs/01-domain/entities/KDDDocument.md")``
    """
    full_path = Path(__file__).resolve().parents[4] / spec_path
    content = full_path.read_text(encoding="utf-8")
    fm, body = extract_frontmatter(content)
    route = route_document(fm, spec_path)
    assert route.kind is not None, f"Could not route {spec_path}"

    sections = parse_markdown_sections(body)
    wiki_links = extract_wiki_link_targets(body)
    layer = detect_layer(spec_path)
    assert layer is not None, f"Could not detect layer for {spec_path}"

    doc_id = fm.get("id", full_path.stem)

    return KDDDocument(
        id=doc_id,
        kind=route.kind,
        source_path=spec_path,
        source_hash=compute_content_hash(content),
        layer=layer,
        front_matter=fm,
        sections=sections,
        wiki_links=wiki_links,
    )
