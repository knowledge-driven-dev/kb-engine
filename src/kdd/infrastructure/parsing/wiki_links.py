"""Wiki-link extraction from markdown content.

Handles two syntaxes:
- ``[[Target]]``         — intra-domain link
- ``[[domain::Target]]`` — cross-domain link
- ``[[Target|Display]]`` — link with display alias

Returns structured results so callers can distinguish link types.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Matches [[...]] allowing nested pipes and double-colons.
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass(frozen=True)
class WikiLink:
    """A parsed wiki-link."""

    raw: str            # full text inside [[ ]]
    target: str         # resolved target name (without domain prefix or alias)
    domain: str | None  # non-None for cross-domain ``[[domain::Target]]``
    alias: str | None   # non-None for ``[[Target|Alias]]``


def extract_wiki_links(content: str) -> list[WikiLink]:
    """Extract all ``[[...]]`` wiki-links from *content*."""
    results: list[WikiLink] = []
    for match in _WIKI_LINK_RE.finditer(content):
        raw = match.group(1).strip()
        if not raw:
            continue

        domain: str | None = None
        alias: str | None = None
        target = raw

        # Cross-domain: [[domain::Target]]
        if "::" in target:
            parts = target.split("::", 1)
            domain = parts[0].strip()
            target = parts[1].strip()

        # Display alias: [[Target|Alias]]
        if "|" in target:
            parts = target.split("|", 1)
            target = parts[0].strip()
            alias = parts[1].strip()

        results.append(WikiLink(
            raw=raw,
            target=target,
            domain=domain,
            alias=alias,
        ))

    return results


def extract_wiki_link_targets(content: str) -> list[str]:
    """Return just the target names from all wiki-links in *content*.

    Convenience wrapper that returns a flat list of strings.
    """
    return [link.target for link in extract_wiki_links(content)]
