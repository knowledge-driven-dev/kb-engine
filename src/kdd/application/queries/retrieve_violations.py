"""QRY-006 — RetrieveLayerViolations.

Detects and reports all edges violating KDD layer dependencies
(BR-LAYER-001).  Corresponds to ``GET /v1/retrieve/layer-violations``.

Spec: specs/02-behavior/queries/QRY-006-RetrieveLayerViolations.md
"""

from __future__ import annotations

from dataclasses import dataclass

from kdd.domain.entities import GraphEdge, LayerViolation
from kdd.domain.enums import KDDKind, KDDLayer
from kdd.domain.ports import GraphStore


@dataclass
class ViolationsQueryInput:
    include_kinds: list[KDDKind] | None = None
    include_layers: list[KDDLayer] | None = None


@dataclass
class ViolationsQueryResult:
    violations: list[LayerViolation]
    total_violations: int
    total_edges_analyzed: int
    violation_rate: float  # percentage


def retrieve_violations(
    query: ViolationsQueryInput,
    graph_store: GraphStore,
) -> ViolationsQueryResult:
    """Execute a layer-violations query (QRY-006)."""
    all_edges = graph_store.all_edges()
    violation_edges = graph_store.find_violations()

    # Apply optional filters — include if EITHER endpoint matches
    if query.include_kinds or query.include_layers:
        filtered: list[GraphEdge] = []
        for edge in violation_edges:
            from_node = graph_store.get_node(edge.from_node)
            to_node = graph_store.get_node(edge.to_node)

            if query.include_kinds:
                from_match = from_node and from_node.kind in query.include_kinds
                to_match = to_node and to_node.kind in query.include_kinds
                if not (from_match or to_match):
                    continue

            if query.include_layers:
                from_match = from_node and from_node.layer in query.include_layers
                to_match = to_node and to_node.layer in query.include_layers
                if not (from_match or to_match):
                    continue

            filtered.append(edge)
        violation_edges = filtered

    # Build violation details
    violations: list[LayerViolation] = []
    for edge in violation_edges:
        from_node = graph_store.get_node(edge.from_node)
        to_node = graph_store.get_node(edge.to_node)

        violations.append(LayerViolation(
            from_node=edge.from_node,
            to_node=edge.to_node,
            from_layer=from_node.layer if from_node else KDDLayer.DOMAIN,
            to_layer=to_node.layer if to_node else KDDLayer.DOMAIN,
            edge_type=edge.edge_type,
        ))

    total = len(all_edges)
    rate = (len(violations) / total * 100) if total > 0 else 0.0

    return ViolationsQueryResult(
        violations=violations,
        total_violations=len(violations),
        total_edges_analyzed=total,
        violation_rate=round(rate, 2),
    )
