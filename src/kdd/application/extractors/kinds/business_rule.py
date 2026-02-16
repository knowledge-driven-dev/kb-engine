"""Business-rule extractor — parses ``kind: business-rule`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → business-rule row.
Indexed fields: declaration, when_applies, violation, examples, formalization.
Edges: ENTITY_RULE, WIKI_LINK.
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


class RuleExtractor:
    """Extractor for ``kind: business-rule`` KDD documents."""

    kind = KDDKind.BUSINESS_RULE

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.BUSINESS_RULE, document.id)
        fields: dict[str, Any] = {}

        decl = find_section(document.sections, "Declaración", "Declaration")
        if decl:
            fields["declaration"] = decl.content

        when = find_section(document.sections, "Cuándo aplica", "When Applies")
        if when:
            fields["when_applies"] = when.content

        why = find_section(document.sections, "Por qué existe", "Why it exists")
        if why:
            fields["why_exists"] = why.content

        violation = find_section(
            document.sections, "Qué pasa si se incumple", "Violation", "What happens if violated"
        )
        if violation:
            fields["violation"] = violation.content

        examples = find_section(document.sections, "Ejemplos", "Examples")
        if examples:
            fields["examples"] = examples.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.BUSINESS_RULE,
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
        node_id = make_node_id(KDDKind.BUSINESS_RULE, document.id)
        edges: list[GraphEdge] = []

        # WIKI_LINK edges
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))

        # ENTITY_RULE: wiki-links to entities in ## Declaración
        decl = find_section(document.sections, "Declaración", "Declaration")
        if decl:
            for link in extract_wiki_links(decl.content):
                # Only link to entities (PascalCase names, not prefixed specs)
                t = link.target
                if not any(t.startswith(p) for p in (
                    "EVT-", "BR-", "BP-", "XP-", "CMD-", "QRY-",
                    "UC-", "PROC-", "REQ-", "OBJ-", "ADR-", "PRD-",
                )):
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
