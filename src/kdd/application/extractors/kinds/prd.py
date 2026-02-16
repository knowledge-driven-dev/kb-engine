"""PRD extractor — parses ``kind: prd`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → prd row.
Indexed fields: problem, scope, users, metrics, dependencies.
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


class PRDExtractor:
    """Extractor for ``kind: prd`` KDD documents."""

    kind = KDDKind.PRD

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.PRD, document.id)
        fields: dict[str, Any] = {}

        problem = find_section(
            document.sections,
            "Problema / Oportunidad", "Problem / Opportunity",
            "Problema", "Problem",
        )
        if problem:
            fields["problem"] = problem.content

        scope = find_section_with_children(
            document.sections, "Alcance", "Scope",
        )
        if scope:
            fields["scope"] = scope

        users = find_section_with_children(
            document.sections,
            "Usuarios y Jobs-to-be-done", "Users and Jobs-to-be-done",
        )
        if users:
            fields["users"] = users

        metrics = find_section(
            document.sections,
            "Métricas de éxito y telemetría", "Success Metrics",
        )
        if metrics:
            fields["metrics"] = metrics.content

        deps = find_section(document.sections, "Dependencias", "Dependencies")
        if deps:
            fields["dependencies"] = deps.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.PRD,
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
        node_id = make_node_id(KDDKind.PRD, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
