"""Use-case extractor — parses ``kind: use-case`` specs.

Spec reference: PRD-KBEngine "Nodos del grafo" → use-case row.
Indexed fields: description, actors, preconditions, main_flow, alternatives,
                exceptions, postconditions.
Edges: UC_APPLIES_RULE, UC_EXECUTES_CMD, UC_STORY, WIKI_LINK.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kdd.application.extractors.base import (
    build_wiki_link_edges,
    find_section,
    find_section_with_children,
    make_node_id,
    resolve_wiki_link_to_node_id,
)
from kdd.application.extractors.kinds.entity import _deduplicate_edges
from kdd.domain.entities import GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import KDDKind
from kdd.infrastructure.parsing.wiki_links import extract_wiki_links


class UseCaseExtractor:
    """Extractor for ``kind: use-case`` KDD documents."""

    kind = KDDKind.USE_CASE

    def extract_node(self, document: KDDDocument) -> GraphNode:
        node_id = make_node_id(KDDKind.USE_CASE, document.id)
        fields: dict[str, Any] = {}

        desc = find_section(document.sections, "Descripción", "Description")
        if desc:
            fields["description"] = desc.content

        actors = find_section(document.sections, "Actores", "Actors")
        if actors:
            fields["actors"] = actors.content

        pre = find_section(document.sections, "Precondiciones", "Preconditions")
        if pre:
            fields["preconditions"] = pre.content

        flow = find_section(document.sections, "Flujo Principal", "Main Flow")
        if flow:
            fields["main_flow"] = flow.content

        alt = find_section_with_children(
            document.sections, "Flujos Alternativos", "Alternative Flows"
        )
        if alt:
            fields["alternatives"] = alt

        exc = find_section_with_children(
            document.sections, "Excepciones", "Exceptions"
        )
        if exc:
            fields["exceptions"] = exc

        post = find_section(document.sections, "Postcondiciones", "Postconditions")
        if post:
            fields["postconditions"] = post.content

        return GraphNode(
            id=node_id,
            kind=KDDKind.USE_CASE,
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
        node_id = make_node_id(KDDKind.USE_CASE, document.id)
        edges: list[GraphEdge] = []

        # WIKI_LINK edges
        edges.extend(build_wiki_link_edges(document, node_id, document.layer))

        # UC_APPLIES_RULE from ## Reglas Aplicadas
        rules_sec = find_section(
            document.sections, "Reglas Aplicadas", "Applied Rules", "Rules Applied"
        )
        if rules_sec:
            for link in extract_wiki_links(rules_sec.content):
                t = link.target
                if t.startswith("BR-") or t.startswith("BP-") or t.startswith("XP-"):
                    to_node = resolve_wiki_link_to_node_id(link)
                    if to_node:
                        edges.append(GraphEdge(
                            from_node=node_id,
                            to_node=to_node,
                            edge_type="UC_APPLIES_RULE",
                            source_file=document.source_path,
                            extraction_method="wiki_link",
                        ))

        # UC_EXECUTES_CMD from ## Comandos Ejecutados
        cmds_sec = find_section(
            document.sections, "Comandos Ejecutados", "Commands Executed"
        )
        if cmds_sec:
            for link in extract_wiki_links(cmds_sec.content):
                if link.target.startswith("CMD-"):
                    to_node = resolve_wiki_link_to_node_id(link)
                    if to_node:
                        edges.append(GraphEdge(
                            from_node=node_id,
                            to_node=to_node,
                            edge_type="UC_EXECUTES_CMD",
                            source_file=document.source_path,
                            extraction_method="wiki_link",
                        ))

        # UC_STORY from OBJ-* wiki-links anywhere in the document
        full_content = "\n".join(s.content for s in document.sections)
        for link in extract_wiki_links(full_content):
            if link.target.startswith("OBJ-"):
                to_node = resolve_wiki_link_to_node_id(link)
                if to_node:
                    edges.append(GraphEdge(
                        from_node=node_id,
                        to_node=to_node,
                        edge_type="UC_STORY",
                        source_file=document.source_path,
                        extraction_method="wiki_link",
                    ))

        return _deduplicate_edges(edges)
