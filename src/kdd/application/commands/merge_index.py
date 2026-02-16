"""CMD-004 — MergeIndex command.

Merges indices from multiple developers into a unified index.
Validates manifest compatibility, resolves node conflicts via
BR-MERGE-001 (last-write-wins / delete-wins), and produces a
new merged IndexManifest.

Spec: specs/02-behavior/commands/CMD-004-MergeIndex.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from kdd.domain.entities import (
    Embedding,
    GraphEdge,
    GraphNode,
    IndexManifest,
    IndexStats,
)
from kdd.domain.enums import IndexLevel
from kdd.domain.rules import resolve_deletion, resolve_node_conflict
from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    total_nodes: int = 0
    total_edges: int = 0
    total_embeddings: int = 0
    conflicts_resolved: int = 0
    error: str | None = None


def merge_index(
    source_paths: list[Path],
    output_path: Path,
    *,
    conflict_strategy: str = "last_write_wins",
) -> MergeResult:
    """Merge multiple .kdd-index/ directories into one.

    Args:
        source_paths: Paths to source .kdd-index/ directories (min 2).
        output_path: Path for the merged output .kdd-index/.
        conflict_strategy: "last_write_wins" or "fail_on_conflict".

    Returns:
        MergeResult with success status and statistics.
    """
    if len(source_paths) < 2:
        return MergeResult(success=False, error="INSUFFICIENT_SOURCES: need at least 2 indices")

    # 1. Load all manifests and validate compatibility
    sources: list[tuple[FilesystemArtifactStore, IndexManifest]] = []
    for path in source_paths:
        store = FilesystemArtifactStore(path)
        manifest = store.read_manifest()
        if manifest is None:
            return MergeResult(success=False, error=f"MANIFEST_NOT_FOUND: {path}")
        sources.append((store, manifest))

    err = _validate_compatibility([m for _, m in sources])
    if err:
        return MergeResult(success=False, error=err)

    # 2. Merge nodes
    all_nodes_by_id: dict[str, list[tuple[int, GraphNode]]] = {}
    for idx, (store, _) in enumerate(sources):
        for node in store.read_all_nodes():
            all_nodes_by_id.setdefault(node.id, []).append((idx, node))

    merged_nodes: list[GraphNode] = []
    conflicts = 0

    for node_id, candidates in all_nodes_by_id.items():
        if len(candidates) == 1:
            merged_nodes.append(candidates[0][1])
            continue

        # Multiple copies — check for conflict
        hashes = {n.source_hash for _, n in candidates}
        if len(hashes) == 1:
            # Identical
            merged_nodes.append(candidates[0][1])
            continue

        # Real conflict
        if conflict_strategy == "fail_on_conflict":
            return MergeResult(
                success=False,
                error=f"CONFLICT_REJECTED: conflict on node {node_id}",
            )

        # Last-write-wins
        conflict_dicts = [
            {
                "source_hash": n.source_hash,
                "indexed_at": n.indexed_at or datetime.min,
            }
            for _, n in candidates
        ]
        result = resolve_node_conflict(conflict_dicts)
        merged_nodes.append(candidates[result.winner_index][1])
        conflicts += 1

    merged_node_ids = {n.id for n in merged_nodes}

    # 3. Merge edges (union, deduplicate, cascade delete for removed nodes)
    seen_edges: set[tuple[str, str, str]] = set()
    merged_edges: list[GraphEdge] = []
    for store, _ in sources:
        for edge in store.read_edges():
            # Cascade: skip edges referencing nodes not in merged set
            if edge.from_node not in merged_node_ids or edge.to_node not in merged_node_ids:
                continue
            key = (edge.from_node, edge.to_node, edge.edge_type)
            if key not in seen_edges:
                seen_edges.add(key)
                merged_edges.append(edge)

    # 4. Merge embeddings (use winner's embeddings for conflicted nodes)
    winner_source: dict[str, int] = {}
    for node_id, candidates in all_nodes_by_id.items():
        if len(candidates) == 1:
            winner_source[node_id] = candidates[0][0]
        else:
            conflict_dicts = [
                {
                    "source_hash": n.source_hash,
                    "indexed_at": n.indexed_at or datetime.min,
                }
                for _, n in candidates
            ]
            result = resolve_node_conflict(conflict_dicts)
            winner_source[node_id] = candidates[result.winner_index][0]

    merged_embeddings: list[Embedding] = []
    for node in merged_nodes:
        doc_id = node.id.split(":", 1)[-1] if ":" in node.id else node.id
        src_idx = winner_source.get(node.id, 0)
        src_store = sources[src_idx][0]
        embs = src_store.read_embeddings(doc_id)
        merged_embeddings.extend(embs)

    # 5. Write merged output
    out_store = FilesystemArtifactStore(output_path)
    for node in merged_nodes:
        out_store.write_node(node)
    if merged_edges:
        out_store.append_edges(merged_edges)
    if merged_embeddings:
        out_store.write_embeddings(merged_embeddings)

    # Determine merged index level (minimum of all sources)
    levels = [m.index_level for _, m in sources]
    merged_level = IndexLevel.L1
    if all(l in (IndexLevel.L2, IndexLevel.L3) for l in levels):
        merged_level = IndexLevel.L2
    if all(l == IndexLevel.L3 for l in levels):
        merged_level = IndexLevel.L3

    # Determine embedding model (must be same across all L2+ sources)
    emb_model = None
    emb_dims = None
    for _, m in sources:
        if m.embedding_model:
            emb_model = m.embedding_model
            emb_dims = m.embedding_dimensions
            break

    manifest = IndexManifest(
        version="1.0.0",
        kdd_version="1.0.0",
        embedding_model=emb_model,
        embedding_dimensions=emb_dims,
        indexed_at=datetime.now(),
        indexed_by="kdd-merge",
        index_level=merged_level,
        stats=IndexStats(
            nodes=len(merged_nodes),
            edges=len(merged_edges),
            embeddings=len(merged_embeddings),
        ),
    )
    out_store.write_manifest(manifest)

    return MergeResult(
        success=True,
        total_nodes=len(merged_nodes),
        total_edges=len(merged_edges),
        total_embeddings=len(merged_embeddings),
        conflicts_resolved=conflicts,
    )


def _validate_compatibility(manifests: list[IndexManifest]) -> str | None:
    """Validate that all manifests are merge-compatible. Returns error or None."""
    # Same major version
    majors = {m.version.split(".")[0] for m in manifests}
    if len(majors) > 1:
        return f"INCOMPATIBLE_VERSION: major versions differ: {majors}"

    # Same embedding model (for L2+ indices)
    models = {m.embedding_model for m in manifests if m.embedding_model}
    if len(models) > 1:
        return f"INCOMPATIBLE_EMBEDDING_MODEL: models differ: {models}"

    # Same structure
    structures = {m.structure for m in manifests}
    if len(structures) > 1:
        return f"INCOMPATIBLE_STRUCTURE: structures differ: {structures}"

    return None
