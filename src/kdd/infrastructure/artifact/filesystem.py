"""Filesystem-based ArtifactStore implementation.

Manages the ``.kdd-index/`` directory layout described in PRD Appendix A::

    .kdd-index/
    ├── manifest.json
    ├── nodes/{kind}/{id}.json
    ├── edges/edges.jsonl
    └── embeddings/{kind}/{doc_id}.json

Implements the ``ArtifactStore`` port from ``kdd.domain.ports``.
"""

from __future__ import annotations

import json
from pathlib import Path

from kdd.domain.entities import Embedding, GraphEdge, GraphNode, IndexManifest
from kdd.domain.enums import KDDKind


class FilesystemArtifactStore:
    """Read/write ``.kdd-index/`` artifacts on the local filesystem."""

    def __init__(self, index_path: str | Path) -> None:
        self._root = Path(index_path)

    @property
    def root(self) -> Path:
        return self._root

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def write_manifest(self, manifest: IndexManifest) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._root / "manifest.json"
        path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def read_manifest(self) -> IndexManifest | None:
        path = self._root / "manifest.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return IndexManifest.model_validate(data)

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def _node_dir(self, kind: KDDKind) -> Path:
        return self._root / "nodes" / kind.value

    def _node_path(self, node: GraphNode) -> Path:
        # ID is "{Kind}:{DocId}" — use DocId as filename
        doc_id = node.id.split(":", 1)[-1] if ":" in node.id else node.id
        return self._node_dir(node.kind) / f"{doc_id}.json"

    def write_node(self, node: GraphNode) -> None:
        path = self._node_path(node)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(node.model_dump_json(indent=2), encoding="utf-8")

    def read_node(self, node_id: str) -> GraphNode | None:
        # Search all kind subdirectories for the node file
        nodes_dir = self._root / "nodes"
        if not nodes_dir.exists():
            return None
        for kind_dir in nodes_dir.iterdir():
            if not kind_dir.is_dir():
                continue
            doc_id = node_id.split(":", 1)[-1] if ":" in node_id else node_id
            path = kind_dir / f"{doc_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return GraphNode.model_validate(data)
        return None

    def read_all_nodes(self) -> list[GraphNode]:
        """Read every node from the store."""
        nodes: list[GraphNode] = []
        nodes_dir = self._root / "nodes"
        if not nodes_dir.exists():
            return nodes
        for kind_dir in nodes_dir.iterdir():
            if not kind_dir.is_dir():
                continue
            for path in sorted(kind_dir.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                nodes.append(GraphNode.model_validate(data))
        return nodes

    # ------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------

    def _edges_path(self) -> Path:
        return self._root / "edges" / "edges.jsonl"

    def append_edges(self, edges: list[GraphEdge]) -> None:
        path = self._edges_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for edge in edges:
                f.write(edge.model_dump_json() + "\n")

    def read_edges(self) -> list[GraphEdge]:
        path = self._edges_path()
        if not path.exists():
            return []
        edges: list[GraphEdge] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                data = json.loads(line)
                edges.append(GraphEdge.model_validate(data))
        return edges

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def _embedding_path(self, kind: KDDKind, document_id: str) -> Path:
        return self._root / "embeddings" / kind.value / f"{document_id}.json"

    def write_embeddings(self, embeddings: list[Embedding]) -> None:
        if not embeddings:
            return
        # Group by (kind, document_id) and write one file per document
        by_doc: dict[tuple[str, str], list[Embedding]] = {}
        for emb in embeddings:
            key = (emb.document_kind.value, emb.document_id)
            by_doc.setdefault(key, []).append(emb)

        for (kind_val, doc_id), doc_embeddings in by_doc.items():
            kind = KDDKind(kind_val)
            path = self._embedding_path(kind, doc_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = [e.model_dump(mode="json") for e in doc_embeddings]
            path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )

    def read_embeddings(self, document_id: str) -> list[Embedding]:
        emb_dir = self._root / "embeddings"
        if not emb_dir.exists():
            return []
        results: list[Embedding] = []
        for kind_dir in emb_dir.iterdir():
            if not kind_dir.is_dir():
                continue
            path = kind_dir / f"{document_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                for item in data:
                    results.append(Embedding.model_validate(item))
        return results

    def read_all_embeddings(self) -> list[Embedding]:
        """Read every embedding from the store."""
        emb_dir = self._root / "embeddings"
        if not emb_dir.exists():
            return []
        results: list[Embedding] = []
        for kind_dir in emb_dir.iterdir():
            if not kind_dir.is_dir():
                continue
            for path in sorted(kind_dir.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                for item in data:
                    results.append(Embedding.model_validate(item))
        return results

    # ------------------------------------------------------------------
    # Cascade delete
    # ------------------------------------------------------------------

    def delete_document_artifacts(self, document_id: str) -> None:
        """Remove a document's node, edges, and embeddings.

        - Deletes the node JSON file.
        - Rewrites ``edges.jsonl`` excluding edges involving this document's node.
        - Deletes the embedding JSON file.
        """
        # 1. Find and delete node file
        nodes_dir = self._root / "nodes"
        if nodes_dir.exists():
            for kind_dir in nodes_dir.iterdir():
                if not kind_dir.is_dir():
                    continue
                path = kind_dir / f"{document_id}.json"
                if path.exists():
                    # Read node to get its ID for edge filtering
                    data = json.loads(path.read_text(encoding="utf-8"))
                    node_id = data.get("id", "")
                    path.unlink()
                    # Remove empty kind directory
                    if not any(kind_dir.iterdir()):
                        kind_dir.rmdir()
                    # 2. Filter edges
                    self._remove_edges_for_node(node_id)
                    break

        # 3. Delete embeddings
        emb_dir = self._root / "embeddings"
        if emb_dir.exists():
            for kind_dir in emb_dir.iterdir():
                if not kind_dir.is_dir():
                    continue
                path = kind_dir / f"{document_id}.json"
                if path.exists():
                    path.unlink()
                    if not any(kind_dir.iterdir()):
                        kind_dir.rmdir()

    def _remove_edges_for_node(self, node_id: str) -> None:
        """Rewrite edges.jsonl excluding edges that reference *node_id*."""
        path = self._edges_path()
        if not path.exists():
            return
        kept: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("from_node") == node_id or data.get("to_node") == node_id:
                continue
            kept.append(line)
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
