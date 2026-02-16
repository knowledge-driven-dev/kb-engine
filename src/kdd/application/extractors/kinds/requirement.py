"""Requirement extractor — parses ``kind: requirement`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → requirement row.
Indexed fields: description, acceptance_criteria, traceability.
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


class RequirementExtractor:
    """Extractor for ``kind: requirement`` KDD documents."""

    kind = KDDKind.REQUIREMENT

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.REQUIREMENT, document.id)
        fields: dict[str, Any] = {}

        desc = find_section(document.sections, "Descripción", "Description")
        if desc:
            fields["description"] = desc.content

        criteria = find_section(
            document.sections,
            "Criterios de Aceptación", "Acceptance Criteria",
        )
        if criteria:
            fields["acceptance_criteria"] = criteria.content

        trace = find_section(document.sections, "Trazabilidad", "Traceability")
        if trace:
            fields["traceability"] = trace.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.REQUIREMENT,
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
        node_id = make_node_id(KDDKind.REQUIREMENT, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
