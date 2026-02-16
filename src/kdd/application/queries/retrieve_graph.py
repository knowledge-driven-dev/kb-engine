"""QRY-001 — RetrieveByGraph.

Graph traversal starting from a root node, following edges by type and
depth.  Corresponds to ``GET /v1/retrieve/graph``.

Spec: specs/02-behavior/queries/QRY-001-RetrieveByGraph.md
"""

from __future__ import annotations

from dataclasses import dataclass

from kdd.domain.entities import GraphEdge, GraphNode, ScoredNode
from kdd.domain.enums import KDDKind
from kdd.domain.ports import GraphStore


@dataclass
class GraphQueryInput:
    root_node: str
    depth: int = 2
    edge_types: list[str] | None = None
    include_kinds: list[KDDKind] | None = None
    respect_layers: bool = True


@dataclass
class GraphQueryResult:
    center_node: GraphNode | None
    related_nodes: list[ScoredNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


def retrieve_by_graph(
    query: GraphQueryInput,
    graph_store: GraphStore,
) -> GraphQueryResult:
    """Execute a graph traversal query (QRY-001).

    Raises ValueError if root_node is not found.
    """
    if not graph_store.has_node(query.root_node):
        raise ValueError(f"NODE_NOT_FOUND: {query.root_node}")

    nodes, edges = graph_store.traverse(
        root=query.root_node,
        depth=query.depth,
        edge_types=query.edge_types,
        respect_layers=query.respect_layers,
    )

    # Filter by kind if requested
    if query.include_kinds:
        kind_set = set(query.include_kinds)
        nodes = [n for n in nodes if n.kind in kind_set]

    center = graph_store.get_node(query.root_node)

    # Score by distance from root (center=1.0, further=lower)
    # We use a simple heuristic: nodes found via BFS get decreasing scores
    scored: list[ScoredNode] = []
    for node in nodes:
        if node.id == query.root_node:
            continue
        # Approximate distance: count hops via shortest edge path
        dist = _estimate_distance(node.id, query.root_node, edges)
        score = 1.0 / (1.0 + dist)
        scored.append(ScoredNode(
            node_id=node.id,
            score=score,
            snippet=_build_snippet(node),
            match_source="graph",
        ))

    scored.sort(key=lambda s: s.score, reverse=True)

    return GraphQueryResult(
        center_node=center,
        related_nodes=scored,
        edges=edges,
        total_nodes=len(scored) + (1 if center else 0),
        total_edges=len(edges),
    )


def _estimate_distance(
    node_id: str,
    root_id: str,
    edges: list[GraphEdge],
) -> int:
    """Rough hop count between root and node via BFS on edge list."""
    from collections import deque

    adj: dict[str, set[str]] = {}
    for e in edges:
        adj.setdefault(e.from_node, set()).add(e.to_node)
        adj.setdefault(e.to_node, set()).add(e.from_node)

    visited = {root_id}
    queue: deque[tuple[str, int]] = deque([(root_id, 0)])
    while queue:
        current, dist = queue.popleft()
        if current == node_id:
            return dist
        for neighbor in adj.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return 999  # unreachable


def _build_snippet(node: GraphNode) -> str:
    """Build a short snippet from node indexed_fields."""
    title = node.indexed_fields.get("title", "")
    if title:
        return f"[{node.kind.value}] {title}"
    return f"[{node.kind.value}] {node.id}"
