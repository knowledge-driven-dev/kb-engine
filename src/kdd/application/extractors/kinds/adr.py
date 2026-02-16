"""ADR extractor — parses ``kind: adr`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → adr row.
Indexed fields: context, decision, consequences.
Edges: WIKI_LINK.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kdd.application.extractors.base import (
    build_wiki_link_edges,
    find_section,
    make_node_id,
)
from kdd.application.extractors.kinds.entity import _deduplicate_edges
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind


class ADRExtractor:
    """Extractor for ``kind: adr`` KDD documents."""

    kind = KDDKind.ADR

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.ADR, document.id)
        fields: dict[str, Any] = {}

        context = find_section(document.sections, "Contexto", "Context")
        if context:
            fields["context"] = context.content

        decision = find_section(document.sections, "Decisión", "Decision")
        if decision:
            fields["decision"] = decision.content

        consequences = find_section(
            document.sections, "Consecuencias", "Consequences",
        )
        if consequences:
            fields["consequences"] = consequences.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.ADR,
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
        node_id = make_node_id(KDDKind.ADR, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
