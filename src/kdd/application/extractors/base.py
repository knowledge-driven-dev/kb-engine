"""Base extractor protocol and helpers.

Every kind-specific extractor implements this protocol so the indexing
pipeline can process any KDD spec uniformly.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument, Section
from kdd.domain.enums import KDDKind, KDDLayer
from kdd.domain.rules import detect_layer, is_layer_violation
from kdd.infrastructure.parsing.wiki_links import WikiLink, extract_wiki_links


class Extractor(Protocol):
    """Protocol that every kind extractor must satisfy."""

    kind: KDDKind

    def extract_node(self, document: KDDDocument) -> GraphNode: ...
    def extract_edges(self, document: KDDDocument) -> list[GraphEdge]: ...


# ---------------------------------------------------------------------------
# Shared helpers available to all extractors
# ---------------------------------------------------------------------------

# Mapping from kind to the ID prefix used in GraphNode.id
KIND_PREFIX: dict[KDDKind, str] = {
    KDDKind.ENTITY: "Entity",
    KDDKind.EVENT: "Event",
    KDDKind.BUSINESS_RULE: "BR",
    KDDKind.BUSINESS_POLICY: "BP",
    KDDKind.CROSS_POLICY: "XP",
    KDDKind.COMMAND: "CMD",
    KDDKind.QUERY: "QRY",
    KDDKind.PROCESS: "PROC",
    KDDKind.USE_CASE: "UC",
    KDDKind.UI_VIEW: "UIView",
    KDDKind.UI_COMPONENT: "UIComp",
    KDDKind.REQUIREMENT: "REQ",
    KDDKind.OBJECTIVE: "OBJ",
    KDDKind.PRD: "PRD",
    KDDKind.ADR: "ADR",
}


def make_node_id(kind: KDDKind, document_id: str) -> str:
    """Build a composite ``{Prefix}:{DocumentId}`` node ID."""
    prefix = KIND_PREFIX.get(kind, kind.value.upper())
    return f"{prefix}:{document_id}"


def find_section(sections: list[Section], *names: str) -> Section | None:
    """Find the first section whose heading matches any of *names* (case-insensitive)."""
    targets = {n.lower() for n in names}
    for s in sections:
        if s.heading.lower() in targets:
            return s
    return None


def find_sections(sections: list[Section], *names: str) -> list[Section]:
    """Return all sections whose heading matches any of *names*."""
    targets = {n.lower() for n in names}
    return [s for s in sections if s.heading.lower() in targets]


def find_section_with_children(
    sections: list[Section], *names: str
) -> str | None:
    """Find a section by heading and concatenate its content with all
    immediate child sub-sections (deeper heading level).

    Returns the combined text, or ``None`` if the parent heading is not found.
    This is useful for sections like ``## Flujos Alternativos`` that have
    sub-headings (``### FA-1``, ``### FA-2``) carrying the actual content.
    """
    targets = {n.lower() for n in names}
    parent_idx: int | None = None
    parent_level: int = 0

    for i, s in enumerate(sections):
        if s.heading.lower() in targets:
            parent_idx = i
            parent_level = s.level
            break

    if parent_idx is None:
        return None

    parts: list[str] = []
    parent = sections[parent_idx]
    if parent.content.strip():
        parts.append(parent.content)

    # Collect children — sections at a deeper level until we hit same or shallower
    for s in sections[parent_idx + 1:]:
        if s.level <= parent_level:
            break
        parts.append(f"### {s.heading}\n\n{s.content}")

    return "\n\n".join(parts) if parts else None


def resolve_wiki_link_to_node_id(link: WikiLink) -> str | None:
    """Best-effort resolution of a wiki-link target to a node ID.

    Heuristics:
    - ``EVT-*``  → ``Event:{target}``
    - ``BR-*``   → ``BR:{target}``
    - ``BP-*``   → ``BP:{target}``
    - ``XP-*``   → ``XP:{target}``
    - ``CMD-*``  → ``CMD:{target}``
    - ``QRY-*``  → ``QRY:{target}``
    - ``UC-*``   → ``UC:{target}``
    - ``PROC-*`` → ``PROC:{target}``
    - ``REQ-*``  → ``REQ:{target}``
    - ``OBJ-*``  → ``OBJ:{target}``
    - ``ADR-*``  → ``ADR:{target}``
    - ``PRD-*``  → ``PRD:{target}``
    - ``UI-*``   → ``UIView:{target}`` (ambiguous, default to view)
    - Otherwise  → ``Entity:{target}`` (PascalCase names are typically entities)
    """
    t = link.target
    prefix_map = [
        ("EVT-", "Event"),
        ("BR-", "BR"),
        ("BP-", "BP"),
        ("XP-", "XP"),
        ("CMD-", "CMD"),
        ("QRY-", "QRY"),
        ("UC-", "UC"),
        ("PROC-", "PROC"),
        ("REQ-", "REQ"),
        ("OBJ-", "OBJ"),
        ("ADR-", "ADR"),
        ("PRD-", "PRD"),
        ("UI-", "UIView"),
    ]
    for prefix, node_prefix in prefix_map:
        if t.startswith(prefix):
            return f"{node_prefix}:{t}"
    return f"Entity:{t}"


def build_wiki_link_edges(
    document: KDDDocument,
    from_node_id: str,
    from_layer: KDDLayer,
) -> list[GraphEdge]:
    """Extract WIKI_LINK edges from all wiki-links in the document body."""
    edges: list[GraphEdge] = []
    seen: set[tuple[str, str]] = set()

    full_content = "\n".join(s.content for s in document.sections)
    links = extract_wiki_links(full_content)

    for link in links:
        to_node_id = resolve_wiki_link_to_node_id(link)
        if to_node_id is None:
            continue
        key = (from_node_id, to_node_id)
        if key in seen:
            continue
        seen.add(key)

        # Determine destination layer heuristically
        dest_layer = _guess_layer_from_node_id(to_node_id)
        violation = False
        if dest_layer is not None:
            violation = is_layer_violation(from_layer, dest_layer)

        metadata: dict[str, Any] = {}
        if link.domain:
            metadata["domain"] = link.domain
        if link.alias:
            metadata["display_alias"] = link.alias

        edges.append(GraphEdge(
            from_node=from_node_id,
            to_node=to_node_id,
            edge_type="WIKI_LINK",
            source_file=document.source_path,
            extraction_method="wiki_link",
            metadata=metadata,
            layer_violation=violation,
            bidirectional=True,
        ))

    return edges


def _guess_layer_from_node_id(node_id: str) -> KDDLayer | None:
    """Guess the KDD layer from a node ID prefix."""
    prefix = node_id.split(":")[0] if ":" in node_id else ""
    layer_map: dict[str, KDDLayer] = {
        "Entity": KDDLayer.DOMAIN,
        "Event": KDDLayer.DOMAIN,
        "BR": KDDLayer.DOMAIN,
        "BP": KDDLayer.BEHAVIOR,
        "XP": KDDLayer.BEHAVIOR,
        "CMD": KDDLayer.BEHAVIOR,
        "QRY": KDDLayer.BEHAVIOR,
        "PROC": KDDLayer.BEHAVIOR,
        "UC": KDDLayer.BEHAVIOR,
        "UIView": KDDLayer.EXPERIENCE,
        "UIComp": KDDLayer.EXPERIENCE,
        "REQ": KDDLayer.VERIFICATION,
        "OBJ": KDDLayer.REQUIREMENTS,
        "PRD": KDDLayer.REQUIREMENTS,
        "ADR": KDDLayer.REQUIREMENTS,
    }
    return layer_map.get(prefix)
