"""Command extractor — parses ``kind: command`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → command row.
Indexed fields: purpose, input_params, preconditions, postconditions, errors.
Edges: EMITS (postcondition events), WIKI_LINK.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kdd.application.extractors.base import (
    build_wiki_link_edges,
    find_section,
    make_node_id,
    resolve_wiki_link_to_node_id,
)
from kdd.application.extractors.kinds.entity import _parse_table_rows, _deduplicate_edges
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind
from kdd.infrastructure.parsing.wiki_links import extract_wiki_links


class CommandExtractor:
    """Extractor for ``kind: command`` KDD documents."""

    kind = KDDKind.COMMAND

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.COMMAND, document.id)
        fields: dict[str, Any] = {}

        purpose = find_section(document.sections, "Purpose", "Propósito")
        if purpose:
            fields["purpose"] = purpose.content

        input_sec = find_section(document.sections, "Input", "Entrada")
        if input_sec:
            fields["input_params"] = _parse_table_rows(input_sec.content)

        pre = find_section(document.sections, "Preconditions", "Precondiciones")
        if pre:
            fields["preconditions"] = pre.content

        post = find_section(document.sections, "Postconditions", "Postcondiciones")
        if post:
            fields["postconditions"] = post.content

        errors = find_section(document.sections, "Possible Errors", "Errores Posibles")
        if errors:
            fields["errors"] = _parse_table_rows(errors.content)

        return GraphNode(
            id=node_id,
            kind=KDDKind.COMMAND,
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
        node_id = make_node_id(KDDKind.COMMAND, document.id)
        edges: list[GraphEdge] = []

        # WIKI_LINK edges
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))

        # EMITS edges from Postconditions (EVT-* wiki-links)
        post = find_section(document.sections, "Postconditions", "Postcondiciones")
        if post:
            for link in extract_wiki_links(post.content):
                if link.target.startswith("EVT-"):
                    to_node = resolve_wiki_link_to_node_id(link)
                    if to_node:
                        edges.append(GraphEdge(
                            from_node=node_id,
                            to_node=to_node,
                            edge_type="EMITS",
                            source_file=document.source_path,
                            extraction_method="wiki_link",
                        ))

        return _deduplicate_edges(edges)
