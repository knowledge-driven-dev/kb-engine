"""Tests for CMD-004 MergeIndex."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kdd.application.commands.merge_index import merge_index
from kdd.domain.entities import (
    Embedding,
    GraphEdge,
    GraphNode,
    IndexManifest,
    IndexStats,
)
from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer
from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore


def _make_manifest(
    *,
    version: str = "1.0.0",
    embedding_model: str | None = "all-MiniLM-L6-v2",
    index_level: IndexLevel = IndexLevel.L1,
    nodes: int = 1,
    edges: int = 1,
) -> IndexManifest:
    return IndexManifest(
        version=version,
        kdd_version="1.0.0",
        embedding_model=embedding_model,
        indexed_at=datetime.now(),
        indexed_by="test",
        index_level=index_level,
        stats=IndexStats(nodes=nodes, edges=edges),
    )


def _make_node(id: str, source_hash: str = "abc", indexed_at: datetime | None = None) -> GraphNode:
    return GraphNode(
        id=id,
        kind=KDDKind.ENTITY,
        source_file=f"{id}.md",
        source_hash=source_hash,
        layer=KDDLayer.DOMAIN,
        indexed_at=indexed_at or datetime.now(),
    )


def _make_edge(from_node: str, to_node: str) -> GraphEdge:
    return GraphEdge(
        from_node=from_node,
        to_node=to_node,
        edge_type="WIKI_LINK",
        source_file="test.md",
        extraction_method="section_content",
    )


def _populate_store(store: FilesystemArtifactStore, manifest, nodes, edges) -> None:
    store.write_manifest(manifest)
    for node in nodes:
        store.write_node(node)
    if edges:
        store.append_edges(edges)


class TestMergeIndexSuccess:
    """Merge without conflicts."""

    def test_merge_disjoint_nodes(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        node_a = _make_node("Entity:A")
        node_b = _make_node("Entity:B")
        edge_ab = _make_edge("Entity:A", "Entity:B")

        _populate_store(s1, _make_manifest(), [node_a], [])
        _populate_store(s2, _make_manifest(), [node_b], [])

        result = merge_index([src1, src2], out)

        assert result.success
        assert result.total_nodes == 2
        assert result.conflicts_resolved == 0

    def test_merge_identical_nodes_no_conflict(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        node = _make_node("Entity:A", source_hash="same_hash")

        _populate_store(s1, _make_manifest(), [node], [])
        _populate_store(s2, _make_manifest(), [node], [])

        result = merge_index([src1, src2], out)

        assert result.success
        assert result.total_nodes == 1
        assert result.conflicts_resolved == 0

    def test_merge_edges_union(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        node_a = _make_node("Entity:A")
        node_b = _make_node("Entity:B")
        node_c = _make_node("Entity:C")

        _populate_store(s1, _make_manifest(), [node_a, node_b], [_make_edge("Entity:A", "Entity:B")])
        _populate_store(s2, _make_manifest(), [node_b, node_c], [_make_edge("Entity:B", "Entity:C")])

        result = merge_index([src1, src2], out)

        assert result.success
        assert result.total_nodes == 3
        assert result.total_edges == 2

    def test_writes_manifest(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        _populate_store(s1, _make_manifest(), [_make_node("Entity:A")], [])
        _populate_store(s2, _make_manifest(), [_make_node("Entity:B")], [])

        merge_index([src1, src2], out)

        out_store = FilesystemArtifactStore(out)
        manifest = out_store.read_manifest()
        assert manifest is not None
        assert manifest.stats.nodes == 2
        assert manifest.indexed_by == "kdd-merge"


class TestMergeConflictResolution:
    """Merge with node conflicts — last-write-wins."""

    def test_last_write_wins(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        old = _make_node("Entity:A", source_hash="old", indexed_at=datetime(2024, 1, 1))
        new = _make_node("Entity:A", source_hash="new", indexed_at=datetime(2025, 1, 1))

        _populate_store(s1, _make_manifest(), [old], [])
        _populate_store(s2, _make_manifest(), [new], [])

        result = merge_index([src1, src2], out)

        assert result.success
        assert result.conflicts_resolved == 1
        assert result.total_nodes == 1

        # Verify the winner
        out_store = FilesystemArtifactStore(out)
        merged_node = out_store.read_node("Entity:A")
        assert merged_node is not None
        assert merged_node.source_hash == "new"

    def test_fail_on_conflict_strategy(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        _populate_store(s1, _make_manifest(), [_make_node("Entity:A", source_hash="v1")], [])
        _populate_store(s2, _make_manifest(), [_make_node("Entity:A", source_hash="v2")], [])

        result = merge_index([src1, src2], out, conflict_strategy="fail_on_conflict")

        assert not result.success
        assert "CONFLICT_REJECTED" in result.error


class TestMergeValidation:
    """Validation of manifest compatibility."""

    def test_insufficient_sources(self, tmp_path):
        result = merge_index([tmp_path / "only_one"], tmp_path / "out")
        assert not result.success
        assert "INSUFFICIENT_SOURCES" in result.error

    def test_missing_manifest(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        src1.mkdir()
        src2.mkdir()

        s1 = FilesystemArtifactStore(src1)
        s1.write_manifest(_make_manifest())

        result = merge_index([src1, src2], tmp_path / "out")
        assert not result.success
        assert "MANIFEST_NOT_FOUND" in result.error

    def test_incompatible_versions(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        _populate_store(s1, _make_manifest(version="1.0.0"), [_make_node("Entity:A")], [])
        _populate_store(s2, _make_manifest(version="2.0.0"), [_make_node("Entity:B")], [])

        result = merge_index([src1, src2], tmp_path / "out")
        assert not result.success
        assert "INCOMPATIBLE_VERSION" in result.error

    def test_incompatible_embedding_models(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        _populate_store(
            s1, _make_manifest(embedding_model="model-a"), [_make_node("Entity:A")], [],
        )
        _populate_store(
            s2, _make_manifest(embedding_model="model-b"), [_make_node("Entity:B")], [],
        )

        result = merge_index([src1, src2], tmp_path / "out")
        assert not result.success
        assert "INCOMPATIBLE_EMBEDDING_MODEL" in result.error


class TestMergeEdgeCascade:
    """Edges referencing removed nodes are dropped."""

    def test_cascade_delete_orphan_edges(self, tmp_path):
        src1, src2 = tmp_path / "idx1", tmp_path / "idx2"
        out = tmp_path / "merged"

        s1 = FilesystemArtifactStore(src1)
        s2 = FilesystemArtifactStore(src2)

        node_a = _make_node("Entity:A")
        node_b = _make_node("Entity:B")

        # src1 has A→B edge, src2 has only node C (B is not in src2)
        _populate_store(s1, _make_manifest(), [node_a, node_b], [_make_edge("Entity:A", "Entity:B")])
        # src2 doesn't have node_b but has an edge referencing a nonexistent node
        _populate_store(
            s2, _make_manifest(), [_make_node("Entity:C")],
            [_make_edge("Entity:C", "Entity:GHOST")],
        )

        result = merge_index([src1, src2], out)
        assert result.success
        # Only the A→B edge survives (both endpoints exist), not C→GHOST
        assert result.total_edges == 1
