"""Event extractor — parses ``kind: event`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → event row.
Indexed fields: description, payload, producer, consumers.
Edges: WIKI_LINK only.
Note: Events produce NO embeddings per BR-EMBEDDING-001.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kdd.application.extractors.base import (
    build_wiki_link_edges,
    find_section,
    make_node_id,
)
from kdd.application.extractors.kinds.entity import (
    _deduplicate_edges,
    _parse_table_rows,
)
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind


class EventExtractor:
    """Extractor for ``kind: event`` KDD documents."""

    kind = KDDKind.EVENT

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.EVENT, document.id)
        fields: dict[str, Any] = {}

        desc = find_section(document.sections, "Descripción", "Description")
        if desc:
            fields["description"] = desc.content

        payload = find_section(document.sections, "Payload")
        if payload:
            fields["payload"] = _parse_table_rows(payload.content)

        producer = find_section(document.sections, "Productor", "Producer")
        if producer:
            fields["producer"] = producer.content

        consumers = find_section(document.sections, "Consumidores", "Consumers")
        if consumers:
            fields["consumers"] = consumers.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.EVENT,
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
        node_id = make_node_id(KDDKind.EVENT, document.id)
        edges: list[GraphEdge] = []
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))
        return _deduplicate_edges(edges)
