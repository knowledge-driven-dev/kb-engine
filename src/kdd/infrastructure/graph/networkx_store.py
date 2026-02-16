"""NetworkX-based GraphStore implementation.

Loads nodes and edges from artifacts into a NetworkX DiGraph for
in-memory querying.  Implements the ``GraphStore`` port.

Used for:
- QRY-001 RetrieveByGraph (BFS traversal)
- QRY-003 RetrieveHybrid (graph expansion phase)
- QRY-004 RetrieveImpact (reverse edge traversal)
- QRY-005 RetrieveCoverage (neighbor analysis)
- QRY-006 RetrieveLayerViolations (violation detection)
"""

from __future__ import annotations

from collections import deque

import networkx as nx

from kdd.domain.entities import GraphEdge, GraphNode


class NetworkXGraphStore:
    """In-memory graph backed by a NetworkX DiGraph."""

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, GraphNode] = {}

    # ------------------------------------------------------------------
    # GraphStore port interface
    # ------------------------------------------------------------------

    def load(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        """Load nodes and edges into the graph, replacing any prior state."""
        self._graph.clear()
        self._nodes.clear()

        for node in nodes:
            self._graph.add_node(node.id, data=node)
            self._nodes[node.id] = node

        for edge in edges:
            self._graph.add_edge(
                edge.from_node,
                edge.to_node,
                data=edge,
            )

    def traverse(
        self,
        root: str,
        depth: int,
        edge_types: list[str] | None = None,
        respect_layers: bool = True,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """BFS traversal from *root* up to *depth* hops.

        Follows both outgoing and incoming edges (undirected traversal)
        so that, e.g., starting from a command you can reach both the
        entities it references and the use-cases that reference it.

        When *respect_layers* is True, edges marked as layer violations
        are excluded from traversal.
        """
        if root not in self._graph:
            return [], []

        visited_nodes: set[str] = {root}
        collected_edges: list[GraphEdge] = []
        queue: deque[tuple[str, int]] = deque([(root, 0)])

        while queue:
            current, dist = queue.popleft()
            if dist >= depth:
                continue

            # Outgoing edges
            for _, neighbor, edata in self._graph.out_edges(current, data=True):
                edge: GraphEdge = edata["data"]
                if not self._edge_matches(edge, edge_types, respect_layers):
                    continue
                collected_edges.append(edge)
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    queue.append((neighbor, dist + 1))

            # Incoming edges (reverse traversal)
            for neighbor, _, edata in self._graph.in_edges(current, data=True):
                edge = edata["data"]
                if not self._edge_matches(edge, edge_types, respect_layers):
                    continue
                collected_edges.append(edge)
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    queue.append((neighbor, dist + 1))

        result_nodes = [
            self._nodes[nid] for nid in visited_nodes if nid in self._nodes
        ]
        # Deduplicate edges (same edge may be encountered from both ends)
        seen_edges: set[tuple[str, str, str]] = set()
        unique_edges: list[GraphEdge] = []
        for e in collected_edges:
            key = (e.from_node, e.to_node, e.edge_type)
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(e)

        return result_nodes, unique_edges

    def text_search(
        self,
        query: str,
        fields: list[str] | None = None,
    ) -> list[GraphNode]:
        """Case-insensitive lexical search over node indexed_fields.

        If *fields* is None, searches all indexed_fields values.
        """
        query_lower = query.lower()
        results: list[GraphNode] = []

        for node in self._nodes.values():
            if self._node_matches_text(node, query_lower, fields):
                results.append(node)

        return results

    def neighbors(self, node_id: str) -> list[GraphNode]:
        """Return all directly connected nodes (successors + predecessors)."""
        if node_id not in self._graph:
            return []
        neighbor_ids: set[str] = set()
        neighbor_ids.update(self._graph.successors(node_id))
        neighbor_ids.update(self._graph.predecessors(node_id))
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def all_edges(self) -> list[GraphEdge]:
        """Return every edge in the graph."""
        return [data["data"] for _, _, data in self._graph.edges(data=True)]

    def find_violations(self) -> list[GraphEdge]:
        """Return all edges marked as layer violations."""
        return [
            data["data"]
            for _, _, data in self._graph.edges(data=True)
            if data["data"].layer_violation
        ]

    # ------------------------------------------------------------------
    # Additional query helpers
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> GraphNode | None:
        """Look up a single node by ID."""
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def incoming_edges(self, node_id: str) -> list[GraphEdge]:
        """Return all edges pointing *to* this node (dependents)."""
        if node_id not in self._graph:
            return []
        return [
            data["data"]
            for _, _, data in self._graph.in_edges(node_id, data=True)
        ]

    def outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        """Return all edges originating *from* this node."""
        if node_id not in self._graph:
            return []
        return [
            data["data"]
            for _, _, data in self._graph.out_edges(node_id, data=True)
        ]

    def reverse_traverse(
        self,
        root: str,
        depth: int,
    ) -> list[tuple[GraphNode, list[GraphEdge]]]:
        """BFS traversal following *incoming* edges only.

        Used by QRY-004 (impact analysis) to find nodes that depend on *root*.
        Returns a list of (node, path_edges) pairs where path_edges is the
        chain of edges from root to that node (in reverse dependency order).
        """
        if root not in self._graph:
            return []

        results: list[tuple[GraphNode, list[GraphEdge]]] = []
        visited: set[str] = {root}
        # (current_node_id, current_depth, path_edges_so_far)
        queue: deque[tuple[str, int, list[GraphEdge]]] = deque([(root, 0, [])])

        while queue:
            current, dist, path = queue.popleft()
            if dist >= depth:
                continue

            for pred, _, edata in self._graph.in_edges(current, data=True):
                if pred in visited:
                    continue
                visited.add(pred)
                edge: GraphEdge = edata["data"]
                new_path = path + [edge]
                if pred in self._nodes:
                    results.append((self._nodes[pred], new_path))
                queue.append((pred, dist + 1, new_path))

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _edge_matches(
        edge: GraphEdge,
        edge_types: list[str] | None,
        respect_layers: bool,
    ) -> bool:
        if respect_layers and edge.layer_violation:
            return False
        if edge_types is not None and edge.edge_type not in edge_types:
            return False
        return True

    @staticmethod
    def _node_matches_text(
        node: GraphNode,
        query_lower: str,
        fields: list[str] | None,
    ) -> bool:
        if fields is not None:
            search_values = [
                str(v)
                for k, v in node.indexed_fields.items()
                if k in fields and v is not None
            ]
        else:
            search_values = [
                str(v)
                for v in node.indexed_fields.values()
                if v is not None
            ]

        # Also search node ID and aliases
        search_values.append(node.id)
        search_values.extend(node.aliases)

        return any(query_lower in val.lower() for val in search_values)
