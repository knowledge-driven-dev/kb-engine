"""Objective extractor — parses ``kind: objective`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → objective row.
Indexed fields: actor, objective, success_criteria.
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


class ObjectiveExtractor:
    """Extractor for ``kind: objective`` KDD documents."""

    kind = KDDKind.OBJECTIVE

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.OBJECTIVE, document.id)
        fields: dict[str, Any] = {}

        actor = find_section(document.sections, "Actor", "Actors")
        if actor:
            fields["actor"] = actor.content

        objective = find_section(document.sections, "Objetivo", "Objective")
        if objective:
            fields["objective"] = objective.content

        criteria = find_section(
            document.sections,
            "Criterios de éxito", "Success Criteria",
        )
        if criteria:
            fields["success_criteria"] = criteria.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.OBJECTIVE,
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
        node_id = make_node_id(KDDKind.OBJECTIVE, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
