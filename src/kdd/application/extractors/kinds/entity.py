"""Entity extractor — parses ``kind: entity`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → entity row.
Indexed fields: description, attributes, relations, invariants, state_machine.
Edges: DOMAIN_RELATION, EMITS, CONSUMES, WIKI_LINK, business relations.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from kdd.application.extractors.base import (
    build_wiki_link_edges,
    find_section,
    make_node_id,
)
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument, Section
from kdd.domain.enums import KDDKind
from kdd.infrastructure.parsing.wiki_links import extract_wiki_links


class EntityExtractor:
    """Extractor for ``kind: entity`` KDD documents."""

    kind = KDDKind.ENTITY

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.ENTITY, document.id)
        fields: dict[str, Any] = {}

        # description
        desc = find_section(document.sections, "Descripción", "Description")
        if desc:
            fields["description"] = desc.content

        # attributes — parse table rows
        attr_sec = find_section(document.sections, "Atributos", "Attributes")
        if attr_sec:
            fields["attributes"] = _parse_table_rows(attr_sec.content)

        # relations — parse table rows
        rel_sec = find_section(document.sections, "Relaciones", "Relations", "Relationships")
        if rel_sec:
            fields["relations"] = _parse_table_rows(rel_sec.content)

        # invariants — list items
        inv_sec = find_section(document.sections, "Invariantes", "Invariants", "Constraints")
        if inv_sec:
            fields["invariants"] = _parse_list_items(inv_sec.content)

        # state_machine — from Ciclo de Vida section
        sm_sec = find_section(document.sections, "Ciclo de Vida", "Lifecycle", "State Machine")
        if sm_sec:
            fields["state_machine"] = sm_sec.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.ENTITY,
            source_file=document.source_path,
            source_hash=document.source_hash,
            layer=document.layer,
            status=document.front_matter.get("status", "draft"),
            aliases=document.front_matter.get("aliases", []),
            domain=document.domain,
            indexed_fields=fields,
            indexed_at=datetime.now(),
        )

    def extract_edges(self, document: KDDDocument) -> list[GraphEdge]:
        node_id = make_node_id(KDDKind.ENTITY, document.id)
        edges: list[GraphEdge] = []

        # 1. WIKI_LINK edges from all content
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))

        # 2. DOMAIN_RELATION from ## Relaciones table
        rel_sec = find_section(document.sections, "Relaciones", "Relations", "Relationships")
        if rel_sec:
            edges.extend(
                _extract_relation_edges(rel_sec, node_id, document.source_path)
            )

        # 3. EMITS / CONSUMES from lifecycle events table or sections
        for section in document.sections:
            heading_lower = section.heading.lower()
            if heading_lower in ("eventos del ciclo de vida", "lifecycle events"):
                edges.extend(
                    _extract_event_edges(section, node_id, document.source_path)
                )

        return _deduplicate_edges(edges)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$", re.MULTILINE)


def _parse_table_rows(content: str) -> list[dict[str, str]]:
    """Parse a Markdown table into a list of dicts."""
    lines = [
        line.strip()
        for line in content.strip().splitlines()
        if line.strip().startswith("|")
    ]
    if len(lines) < 2:
        return []

    headers = [h.strip().strip("`") for h in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:  # skip separator line
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def _parse_list_items(content: str) -> list[str]:
    """Extract ``- item`` list items from Markdown content."""
    items: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
    return items


def _extract_relation_edges(
    section: Section, from_node: str, source_file: str,
) -> list[GraphEdge]:
    """Extract DOMAIN_RELATION and business edges from a relations table."""
    edges: list[GraphEdge] = []
    rows = _parse_table_rows(section.content)
    for row in rows:
        # Find target entity in any column containing [[...]]
        target = None
        for val in row.values():
            links = extract_wiki_links(val)
            if links:
                from kdd.application.extractors.base import resolve_wiki_link_to_node_id
                target = resolve_wiki_link_to_node_id(links[0])
                break
        if not target:
            continue

        # Relation name (first column usually)
        rel_name = next(iter(row.values()), "")
        cardinality = row.get("Cardinalidad", row.get("Cardinality", ""))

        edges.append(GraphEdge(
            from_node=from_node,
            to_node=target,
            edge_type="DOMAIN_RELATION",
            source_file=source_file,
            extraction_method="section_content",
            metadata={"relation": rel_name, "cardinality": cardinality},
        ))

    return edges


def _extract_event_edges(
    section: Section, from_node: str, source_file: str,
) -> list[GraphEdge]:
    """Extract EMITS edges from lifecycle event tables/lists."""
    edges: list[GraphEdge] = []
    links = extract_wiki_links(section.content)
    for link in links:
        if link.target.startswith("EVT-"):
            from kdd.application.extractors.base import resolve_wiki_link_to_node_id
            to_node = resolve_wiki_link_to_node_id(link)
            if to_node:
                edges.append(GraphEdge(
                    from_node=from_node,
                    to_node=to_node,
                    edge_type="EMITS",
                    source_file=source_file,
                    extraction_method="wiki_link",
                ))
    return edges


def _deduplicate_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    """Remove duplicate edges (same from/to/type)."""
    seen: set[tuple[str, str, str]] = set()
    result: list[GraphEdge] = []
    for e in edges:
        key = (e.from_node, e.to_node, e.edge_type)
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result
