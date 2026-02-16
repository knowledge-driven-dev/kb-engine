"""UI-component extractor — parses ``kind: ui-component`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → ui-component row.
Indexed fields: description, entities, use_cases.
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


class UIComponentExtractor:
    """Extractor for ``kind: ui-component`` KDD documents."""

    kind = KDDKind.UI_COMPONENT

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.UI_COMPONENT, document.id)
        fields: dict[str, Any] = {}

        desc = find_section(document.sections, "Descripción", "Description")
        if desc:
            fields["description"] = desc.content

        entities = find_section(document.sections, "Entidades", "Entities")
        if entities:
            fields["entities"] = entities.content

        use_cases = find_section(document.sections, "Casos de Uso", "Use Cases")
        if use_cases:
            fields["use_cases"] = use_cases.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.UI_COMPONENT,
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
        node_id = make_node_id(KDDKind.UI_COMPONENT, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
