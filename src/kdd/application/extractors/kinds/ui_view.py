"""UI-view extractor — parses ``kind: ui-view`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → ui-view row.
Indexed fields: description, layout, components, states, behavior.
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


class UIViewExtractor:
    """Extractor for ``kind: ui-view`` KDD documents."""

    kind = KDDKind.UI_VIEW

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.UI_VIEW, document.id)
        fields: dict[str, Any] = {}

        desc = find_section(document.sections, "Descripción", "Description")
        if desc:
            fields["description"] = desc.content

        layout = find_section(document.sections, "Layout", "Diseño")
        if layout:
            fields["layout"] = layout.content

        components = find_section(document.sections, "Componentes", "Components")
        if components:
            fields["components"] = components.content

        states = find_section(document.sections, "Estados", "States")
        if states:
            fields["states"] = states.content

        behavior = find_section(document.sections, "Comportamiento", "Behavior")
        if behavior:
            fields["behavior"] = behavior.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.UI_VIEW,
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
        node_id = make_node_id(KDDKind.UI_VIEW, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
