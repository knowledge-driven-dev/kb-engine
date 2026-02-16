"""Tests for IndexLoader."""

from datetime import datetime

import pytest

from kdd.application.queries.index_loader import IndexLoader
from kdd.domain.entities import (
    Embedding,
    GraphEdge,
    GraphNode,
    IndexManifest,
    IndexStats,
)
from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer
from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore
from kdd.infrastructure.graph.networkx_store import NetworkXGraphStore
from kdd.infrastructure.vector.hnswlib_store import HNSWLibVectorStore


@pytest.fixture
def artifact_dir(tmp_path):
    return tmp_path / ".kdd-index"


@pytest.fixture
def populated_artifacts(artifact_dir):
    """Write minimal artifacts to disk."""
    store = FilesystemArtifactStore(artifact_dir)

    manifest = IndexManifest(
        version="1.0.0",
        kdd_version="1.0",
        indexed_at=datetime.now(),
        indexed_by="test",
        index_level=IndexLevel.L1,
        stats=IndexStats(nodes=1, edges=1, embeddings=0),
    )
    store.write_manifest(manifest)

    node = GraphNode(
        id="Entity:Test",
        kind=KDDKind.ENTITY,
        source_file="test.md",
        source_hash="abc",
        layer=KDDLayer.DOMAIN,
        indexed_fields={"title": "Test"},
    )
    store.write_node(node)

    edge = GraphEdge(
        from_node="Entity:Test",
        to_node="BR:BR-001",
        edge_type="ENTITY_RULE",
        source_file="test.md",
        extraction_method="section_content",
    )
    store.append_edges([edge])

    return store


class TestIndexLoader:
    def test_load_populates_graph(self, populated_artifacts, artifact_dir):
        graph = NetworkXGraphStore()
        loader = IndexLoader(populated_artifacts, graph)

        assert not loader.is_loaded
        loaded = loader.load()
        assert loaded
        assert loader.is_loaded
        assert graph.node_count() == 1
        assert graph.has_node("Entity:Test")

    def test_load_caches(self, populated_artifacts, artifact_dir):
        graph = NetworkXGraphStore()
        loader = IndexLoader(populated_artifacts, graph)

        loader.load()
        assert not loader.load()  # second call uses cache

    def test_reload_forces_refresh(self, populated_artifacts, artifact_dir):
        graph = NetworkXGraphStore()
        loader = IndexLoader(populated_artifacts, graph)

        loader.load()
        assert loader.reload()  # forced reload

    def test_load_without_manifest(self, artifact_dir):
        store = FilesystemArtifactStore(artifact_dir)
        graph = NetworkXGraphStore()
        loader = IndexLoader(store, graph)

        loaded = loader.load()
        assert not loaded
        assert not loader.is_loaded

    def test_load_with_vector_store(self, artifact_dir):
        store = FilesystemArtifactStore(artifact_dir)

        # Write manifest and node
        manifest = IndexManifest(
            version="1.0.0",
            kdd_version="1.0",
            indexed_at=datetime.now(),
            indexed_by="test",
            index_level=IndexLevel.L2,
            embedding_model="test-model",
            embedding_dimensions=4,
            stats=IndexStats(nodes=1, edges=0, embeddings=1),
        )
        store.write_manifest(manifest)

        node = GraphNode(
            id="Entity:Test",
            kind=KDDKind.ENTITY,
            source_file="test.md",
            source_hash="abc",
            layer=KDDLayer.DOMAIN,
        )
        store.write_node(node)

        emb = Embedding(
            id="Test:chunk-0",
            document_id="Test",
            document_kind=KDDKind.ENTITY,
            section_path="Descripción",
            chunk_index=0,
            raw_text="test",
            context_text="test context",
            vector=[1.0, 0.0, 0.0, 0.0],
            model="test-model",
            dimensions=4,
            text_hash="hash",
            generated_at=datetime.now(),
        )
        store.write_embeddings([emb])

        graph = NetworkXGraphStore()
        vector = HNSWLibVectorStore()
        loader = IndexLoader(store, graph, vector)

        loader.load()
        assert graph.node_count() == 1
        assert vector.size == 1
