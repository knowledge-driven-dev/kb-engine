"""Cross-policy extractor — parses ``kind: cross-policy`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → cross-policy row.
Indexed fields: purpose, declaration, formalization_ears, standard_behavior.
Edges: ENTITY_RULE (entities in declaration), WIKI_LINK.
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
from kdd.application.extractors.kinds.entity import _deduplicate_edges
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind
from kdd.infrastructure.parsing.wiki_links import extract_wiki_links


class CrossPolicyExtractor:
    """Extractor for ``kind: cross-policy`` KDD documents."""

    kind = KDDKind.CROSS_POLICY

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.CROSS_POLICY, document.id)
        fields: dict[str, Any] = {}

        purpose = find_section(document.sections, "Propósito", "Purpose")
        if purpose:
            fields["purpose"] = purpose.content

        decl = find_section(document.sections, "Declaración", "Declaration")
        if decl:
            fields["declaration"] = decl.content

        formal = find_section(
            document.sections,
            "Formalización EARS", "EARS Formalization",
        )
        if formal:
            fields["formalization_ears"] = formal.content

        behavior = find_section(
            document.sections,
            "Comportamiento Estándar", "Standard Behavior",
        )
        if behavior:
            fields["standard_behavior"] = behavior.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.CROSS_POLICY,
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
        node_id = make_node_id(KDDKind.CROSS_POLICY, document.id)
        edges: list[GraphEdge] = []

        edges.extend(build_wiki_link_edges(document, node_id, document.layer))

        # ENTITY_RULE from declaration section
        decl = find_section(document.sections, "Declaración", "Declaration")
        if decl:
            for link in extract_wiki_links(decl.content):
                t = link.target
                if not t.startswith(("EVT-", "BR-", "BP-", "XP-", "CMD-", "QRY-",
                                     "UC-", "PROC-", "REQ-", "OBJ-", "ADR-", "PRD-", "UI-")):
                    to_node = resolve_wiki_link_to_node_id(link)
                    if to_node:
                        edges.append(GraphEdge(
                            from_node=node_id,
                            to_node=to_node,
                            edge_type="ENTITY_RULE",
                            source_file=document.source_path,
                            extraction_method="wiki_link",
                        ))

        return _deduplicate_edges(edges)
