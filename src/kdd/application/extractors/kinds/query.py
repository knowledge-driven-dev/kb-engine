"""Query extractor — parses ``kind: query`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → query row.
Indexed fields: purpose, input_params, output_structure, errors.
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
from kdd.application.extractors.kinds.entity import _parse_table_rows, _deduplicate_edges
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind


class QueryExtractor:
    """Extractor for ``kind: query`` KDD documents."""

    kind = KDDKind.QUERY

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.QUERY, document.id)
        fields: dict[str, Any] = {}

        purpose = find_section(document.sections, "Purpose", "Propósito")
        if purpose:
            fields["purpose"] = purpose.content

        input_sec = find_section(document.sections, "Input", "Entrada")
        if input_sec:
            fields["input_params"] = _parse_table_rows(input_sec.content)

        output_sec = find_section(document.sections, "Output", "Salida")
        if output_sec:
            fields["output_structure"] = output_sec.content

        errors = find_section(document.sections, "Possible Errors", "Errores Posibles")
        if errors:
            fields["errors"] = _parse_table_rows(errors.content)

        return GraphNode(
            id=node_id,
            kind=KDDKind.QUERY,
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
        node_id = make_node_id(KDDKind.QUERY, document.id)
        edges = build_wiki_link_edges(document, node_id, document.layer)
        return _deduplicate_edges(edges)
