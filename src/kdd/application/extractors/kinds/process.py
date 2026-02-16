"""Process extractor — parses ``kind: process`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → process row.
Indexed fields: participants, steps, mermaid_flow.
Edges: WIKI_LINK.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kdd.application.extractors.base import (
    build_wiki_link_edges,
    find_section,
    find_section_with_children,
    make_node_id,
)
from kdd.application.extractors.kinds.entity import _deduplicate_edges
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind


class ProcessExtractor:
    """Extractor for ``kind: process`` KDD documents."""

    kind = KDDKind.PROCESS

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.PROCESS, document.id)
        fields: dict[str, Any] = {}

        participants = find_section(
            document.sections, "Participantes", "Participants",
        )
        if participants:
            fields["participants"] = participants.content

        steps = find_section_with_children(
            document.sections, "Pasos", "Steps",
        )
        if steps:
            fields["steps"] = steps

        diagram = find_section(document.sections, "Diagrama", "Diagram")
        if diagram:
            fields["mermaid_flow"] = diagram.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.PROCESS,
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
        node_id = make_node_id(KDDKind.PROCESS, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
