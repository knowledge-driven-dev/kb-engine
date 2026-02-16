"""Markdown parsing utilities.

Ported from ``kb_engine/utils/markdown.py`` with wiki-link awareness removed
(wiki-links have their own module) and Section dataclass integration.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import frontmatter

from kdd.domain.entities import Section


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML front-matter from markdown content.

    Returns ``(metadata_dict, body_without_frontmatter)``.
    If parsing fails, returns ``({}, original_content)``.
    """
    try:
        post = frontmatter.loads(content)
        return dict(post.metadata), post.content
    except Exception:
        return {}, content


def parse_markdown_sections(content: str) -> list[Section]:
    """Parse markdown body into a list of :class:`Section` objects.

    Each section captures its heading text, heading level (1-6), the raw
    content below it, and a dot-separated hierarchical ``path`` built from
    the heading ancestry (e.g. ``"descripción.atributos"``).
    """
    sections: list[Section] = []
    current_headings: list[str] = []
    current_levels: list[int] = []
    current_lines: list[str] = []

    def _flush() -> None:
        text = "\n".join(current_lines).strip()
        if current_headings:
            path = ".".join(
                heading_to_anchor(h) for h in current_headings
            )
            sections.append(Section(
                heading=current_headings[-1],
                level=current_levels[-1] if current_levels else 1,
                content=text,
                path=path,
            ))

    for line in content.split("\n"):
        if line.startswith("#"):
            _flush()
            current_lines = []

            level = len(line) - len(line.lstrip("#"))
            heading_text = line.lstrip("#").strip()

            # Maintain hierarchy: pop deeper or equal headings
            while current_levels and current_levels[-1] >= level:
                current_levels.pop()
                if current_headings:
                    current_headings.pop()

            current_headings.append(heading_text)
            current_levels.append(level)
        else:
            current_lines.append(line)

    _flush()
    return sections


def heading_to_anchor(heading: str) -> str:
    """Convert a heading to a GitHub-compatible anchor slug.

    Algorithm: lowercase → strip non-alphanumeric (keep spaces/hyphens)
    → spaces to hyphens → strip trailing hyphens.
    """
    text = unicodedata.normalize("NFKD", heading)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = text.strip("-")
    return text


def extract_snippet(content: str, max_length: int = 200) -> str:
    """Extract a plain-text snippet from markdown content.

    Strips formatting, truncates at sentence or word boundary.
    """
    text = content.strip()
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    last_period = truncated.rfind(". ")
    if last_period > max_length // 2:
        return truncated[: last_period + 1]

    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        return truncated[:last_space] + "..."

    return truncated + "..."
