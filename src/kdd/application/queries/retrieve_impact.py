"""QRY-004 — RetrieveImpact.

Impact analysis from a node.  Returns all directly and transitively
affected nodes, dependency chains, and BDD scenarios to re-run.
Corresponds to ``GET /v1/retrieve/impact``.

Spec: specs/02-behavior/queries/QRY-004-RetrieveImpact.md
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kdd.domain.entities import GraphEdge, GraphNode, ScoredNode
from kdd.domain.enums import EdgeType
from kdd.domain.ports import GraphStore


@dataclass
class AffectedNode:
    """A node affected by a change, with the dependency path."""

    node_id: str
    kind: str
    edge_type: str
    impact_description: str


@dataclass
class TransitivelyAffected:
    """A node transitively affected, with the full dependency chain."""

    node_id: str
    kind: str
    path: list[str]  # node IDs from root to this node
    edge_types: list[str]  # edge types along the path


@dataclass
class ScenarioToRerun:
    """A BDD scenario that should be re-run after a change."""

    node_id: str
    scenario_name: str
    reason: str


@dataclass
class ImpactQueryInput:
    node_id: str
    change_type: str = "modify_attribute"
    depth: int = 3


@dataclass
class ImpactQueryResult:
    analyzed_node: GraphNode | None
    directly_affected: list[AffectedNode]
    transitively_affected: list[TransitivelyAffected]
    scenarios_to_rerun: list[ScenarioToRerun]
    total_directly: int
    total_transitively: int


def retrieve_impact(
    query: ImpactQueryInput,
    graph_store: GraphStore,
) -> ImpactQueryResult:
    """Execute an impact analysis query (QRY-004).

    Follows *incoming* edges to find nodes that depend on the queried node.
    """
    if not graph_store.has_node(query.node_id):
        raise ValueError(f"NODE_NOT_FOUND: {query.node_id}")

    analyzed = graph_store.get_node(query.node_id)

    # Phase 1: Direct dependents (nodes with edges pointing TO query.node_id)
    direct_edges = graph_store.incoming_edges(query.node_id)
    directly_affected: list[AffectedNode] = []
    direct_ids: set[str] = set()

    for edge in direct_edges:
        pred_node = graph_store.get_node(edge.from_node)
        if pred_node is None:
            continue
        direct_ids.add(pred_node.id)
        directly_affected.append(AffectedNode(
            node_id=pred_node.id,
            kind=pred_node.kind.value,
            edge_type=edge.edge_type,
            impact_description=_describe_impact(edge, query.change_type),
        ))

    # Phase 2: Transitive dependents (BFS on incoming edges beyond depth 1)
    transitively_affected: list[TransitivelyAffected] = []
    if query.depth > 1:
        reverse_results = graph_store.reverse_traverse(query.node_id, query.depth)
        for node, path_edges in reverse_results:
            if node.id in direct_ids or node.id == query.node_id:
                continue
            path_ids = [query.node_id]
            edge_types = []
            for e in path_edges:
                path_ids.append(e.from_node)
                edge_types.append(e.edge_type)
            transitively_affected.append(TransitivelyAffected(
                node_id=node.id,
                kind=node.kind.value,
                path=path_ids,
                edge_types=edge_types,
            ))

    # Phase 3: Find BDD scenarios (nodes with VALIDATES edges)
    scenarios: list[ScenarioToRerun] = []
    all_affected_ids = direct_ids | {t.node_id for t in transitively_affected}
    all_affected_ids.add(query.node_id)

    for edge in graph_store.all_edges():
        if edge.edge_type == EdgeType.VALIDATES.value:
            if edge.to_node in all_affected_ids:
                feature_node = graph_store.get_node(edge.from_node)
                if feature_node:
                    scenarios.append(ScenarioToRerun(
                        node_id=feature_node.id,
                        scenario_name=feature_node.indexed_fields.get("title", feature_node.id),
                        reason=f"Validates {edge.to_node} which is affected",
                    ))

    return ImpactQueryResult(
        analyzed_node=analyzed,
        directly_affected=directly_affected,
        transitively_affected=transitively_affected,
        scenarios_to_rerun=scenarios,
        total_directly=len(directly_affected),
        total_transitively=len(transitively_affected),
    )


def _describe_impact(edge: GraphEdge, change_type: str) -> str:
    """Generate a human-readable impact description."""
    type_desc = {
        "ENTITY_RULE": "Business rule validates this entity",
        "UC_APPLIES_RULE": "Use case applies this rule",
        "UC_EXECUTES_CMD": "Use case executes this command",
        "EMITS": "Emits this event",
        "CONSUMES": "Consumes this event",
        "WIKI_LINK": "References this artifact",
        "DOMAIN_RELATION": "Has a domain relationship",
        "REQ_TRACES_TO": "Requirement traces to this artifact",
        "VALIDATES": "Validates this artifact via BDD scenarios",
    }
    desc = type_desc.get(edge.edge_type, f"Connected via {edge.edge_type}")
    return f"{desc} — change type: {change_type}"
