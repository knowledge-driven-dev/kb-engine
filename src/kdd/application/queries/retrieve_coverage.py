"""QRY-005 — RetrieveCoverage.

Validates governance coverage for a node.  Determines what related
artifacts **should exist** for a given kind and which are missing.
Corresponds to ``GET /v1/retrieve/coverage``.

Spec: specs/02-behavior/queries/QRY-005-RetrieveCoverage.md
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kdd.domain.entities import GraphNode
from kdd.domain.enums import EdgeType, KDDKind
from kdd.domain.ports import GraphStore


@dataclass
class CoverageCategory:
    """A required category of related artifacts."""

    name: str
    description: str
    edge_type: str
    status: str  # "covered", "missing", "partial"
    found: list[str]  # node IDs


@dataclass
class CoverageQueryInput:
    node_id: str


@dataclass
class CoverageQueryResult:
    analyzed_node: GraphNode | None
    categories: list[CoverageCategory]
    present: int
    missing: int
    coverage_percent: float


# Coverage rules per kind: which related artifact types should exist
_COVERAGE_RULES: dict[KDDKind, list[tuple[str, str, str]]] = {
    # (category_name, description, edge_type_to_check)
    KDDKind.ENTITY: [
        ("events", "Domain events emitted by this entity", EdgeType.EMITS.value),
        ("business_rules", "Business rules for this entity", EdgeType.ENTITY_RULE.value),
        ("use_cases", "Use cases involving this entity", EdgeType.WIKI_LINK.value),
    ],
    KDDKind.COMMAND: [
        ("events", "Events emitted by this command", EdgeType.EMITS.value),
        ("use_cases", "Use cases that execute this command", EdgeType.UC_EXECUTES_CMD.value),
    ],
    KDDKind.USE_CASE: [
        ("commands", "Commands executed by this use case", EdgeType.UC_EXECUTES_CMD.value),
        ("rules", "Business rules applied", EdgeType.UC_APPLIES_RULE.value),
        ("requirements", "Requirements tracing to this UC", EdgeType.REQ_TRACES_TO.value),
    ],
    KDDKind.BUSINESS_RULE: [
        ("entity", "Entity this rule validates", EdgeType.ENTITY_RULE.value),
        ("use_cases", "Use cases that apply this rule", EdgeType.UC_APPLIES_RULE.value),
    ],
    KDDKind.REQUIREMENT: [
        ("traces", "Artifacts this requirement traces to", EdgeType.REQ_TRACES_TO.value),
    ],
}


def retrieve_coverage(
    query: CoverageQueryInput,
    graph_store: GraphStore,
) -> CoverageQueryResult:
    """Execute a coverage analysis query (QRY-005).

    Raises ValueError if node not found or kind has no coverage rules.
    """
    if not graph_store.has_node(query.node_id):
        raise ValueError(f"NODE_NOT_FOUND: {query.node_id}")

    node = graph_store.get_node(query.node_id)
    if node is None:
        raise ValueError(f"NODE_NOT_FOUND: {query.node_id}")

    rules = _COVERAGE_RULES.get(node.kind)
    if rules is None:
        raise ValueError(f"UNKNOWN_KIND: no coverage rules for kind '{node.kind.value}'")

    # Collect all edges involving this node
    incoming = graph_store.incoming_edges(query.node_id)
    outgoing = graph_store.outgoing_edges(query.node_id)
    all_edges = incoming + outgoing

    categories: list[CoverageCategory] = []
    present = 0
    missing = 0

    for cat_name, cat_desc, edge_type in rules:
        # Find edges of this type connecting to/from our node
        found_ids: list[str] = []
        for edge in all_edges:
            if edge.edge_type == edge_type:
                other = edge.to_node if edge.from_node == query.node_id else edge.from_node
                if other not in found_ids:
                    found_ids.append(other)

        if found_ids:
            status = "covered"
            present += 1
        else:
            status = "missing"
            missing += 1

        categories.append(CoverageCategory(
            name=cat_name,
            description=cat_desc,
            edge_type=edge_type,
            status=status,
            found=found_ids,
        ))

    total = present + missing
    coverage_pct = (present / total * 100) if total > 0 else 0.0

    return CoverageQueryResult(
        analyzed_node=node,
        categories=categories,
        present=present,
        missing=missing,
        coverage_percent=round(coverage_pct, 1),
    )
