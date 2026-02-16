"""Tests for kdd.infrastructure.artifact.filesystem."""

from datetime import datetime

import pytest

from kdd.domain.entities import Embedding, GraphEdge, GraphNode, IndexManifest, IndexStats
from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer
from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore


@pytest.fixture
def store(tmp_path):
    """An ArtifactStore rooted in a temp directory."""
    return FilesystemArtifactStore(tmp_path / ".kdd-index")


@pytest.fixture
def sample_manifest():
    return IndexManifest(
        version="1.0.0",
        kdd_version="1.0",
        indexed_at=datetime(2026, 2, 15, 10, 0, 0),
        indexed_by="test-dev",
        index_level=IndexLevel.L1,
        stats=IndexStats(nodes=2, edges=3),
    )


@pytest.fixture
def sample_node():
    return GraphNode(
        id="Entity:Pedido",
        kind=KDDKind.ENTITY,
        source_file="specs/01-domain/entities/Pedido.md",
        source_hash="abc123",
        layer=KDDLayer.DOMAIN,
        indexed_fields={"description": "An order"},
        indexed_at=datetime(2026, 2, 15, 10, 0, 0),
    )


@pytest.fixture
def sample_edges():
    return [
        GraphEdge(
            from_node="Entity:Pedido",
            to_node="Entity:Usuario",
            edge_type="DOMAIN_RELATION",
            source_file="specs/01-domain/entities/Pedido.md",
            extraction_method="section_content",
        ),
        GraphEdge(
            from_node="Entity:Pedido",
            to_node="Event:EVT-Pedido-Creado",
            edge_type="EMITS",
            source_file="specs/01-domain/entities/Pedido.md",
            extraction_method="wiki_link",
        ),
    ]


@pytest.fixture
def sample_embedding():
    return Embedding(
        id="Pedido:descripcion:0",
        document_id="Pedido",
        document_kind=KDDKind.ENTITY,
        section_path="descripcion",
        chunk_index=0,
        raw_text="An order placed by a user",
        context_text="[entity: Pedido] > An order placed by a user",
        vector=[0.1] * 10,
        model="test-model",
        dimensions=10,
        text_hash="h1",
        generated_at=datetime(2026, 2, 15, 10, 0, 0),
    )


class TestManifestRoundTrip:
    def test_write_and_read(self, store, sample_manifest):
        store.write_manifest(sample_manifest)
        loaded = store.read_manifest()
        assert loaded is not None
        assert loaded.version == "1.0.0"
        assert loaded.indexed_by == "test-dev"
        assert loaded.stats.nodes == 2

    def test_read_nonexistent(self, store):
        assert store.read_manifest() is None

    def test_creates_directory(self, store, sample_manifest):
        store.write_manifest(sample_manifest)
        assert (store.root / "manifest.json").exists()


class TestNodeRoundTrip:
    def test_write_and_read(self, store, sample_node):
        store.write_node(sample_node)
        loaded = store.read_node("Entity:Pedido")
        assert loaded is not None
        assert loaded.id == "Entity:Pedido"
        assert loaded.kind == KDDKind.ENTITY
        assert loaded.indexed_fields["description"] == "An order"

    def test_read_nonexistent(self, store):
        assert store.read_node("Entity:Missing") is None

    def test_file_structure(self, store, sample_node):
        store.write_node(sample_node)
        path = store.root / "nodes" / "entity" / "Pedido.json"
        assert path.exists()

    def test_read_all_nodes(self, store, sample_node):
        store.write_node(sample_node)
        node2 = GraphNode(
            id="CMD:CMD-001",
            kind=KDDKind.COMMAND,
            source_file="specs/02-behavior/commands/CMD-001.md",
            source_hash="def456",
            layer=KDDLayer.BEHAVIOR,
        )
        store.write_node(node2)
        all_nodes = store.read_all_nodes()
        assert len(all_nodes) == 2
        ids = {n.id for n in all_nodes}
        assert "Entity:Pedido" in ids
        assert "CMD:CMD-001" in ids


class TestEdgeRoundTrip:
    def test_append_and_read(self, store, sample_edges):
        store.append_edges(sample_edges)
        loaded = store.read_edges()
        assert len(loaded) == 2
        assert loaded[0].from_node == "Entity:Pedido"
        assert loaded[1].edge_type == "EMITS"

    def test_append_multiple_times(self, store, sample_edges):
        store.append_edges(sample_edges[:1])
        store.append_edges(sample_edges[1:])
        loaded = store.read_edges()
        assert len(loaded) == 2

    def test_read_empty(self, store):
        assert store.read_edges() == []

    def test_jsonl_format(self, store, sample_edges):
        store.append_edges(sample_edges)
        path = store.root / "edges" / "edges.jsonl"
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2


class TestEmbeddingRoundTrip:
    def test_write_and_read(self, store, sample_embedding):
        store.write_embeddings([sample_embedding])
        loaded = store.read_embeddings("Pedido")
        assert len(loaded) == 1
        assert loaded[0].id == "Pedido:descripcion:0"
        assert len(loaded[0].vector) == 10

    def test_read_empty(self, store):
        assert store.read_embeddings("Missing") == []

    def test_file_structure(self, store, sample_embedding):
        store.write_embeddings([sample_embedding])
        path = store.root / "embeddings" / "entity" / "Pedido.json"
        assert path.exists()

    def test_write_empty_list(self, store):
        store.write_embeddings([])
        assert not (store.root / "embeddings").exists()


class TestCascadeDelete:
    def test_deletes_node_edges_embeddings(
        self, store, sample_node, sample_edges, sample_embedding
    ):
        # Setup
        store.write_node(sample_node)
        store.append_edges(sample_edges)
        store.write_embeddings([sample_embedding])

        # Act
        store.delete_document_artifacts("Pedido")

        # Assert: node gone
        assert store.read_node("Entity:Pedido") is None

        # Assert: edges involving Pedido removed
        remaining_edges = store.read_edges()
        for edge in remaining_edges:
            assert "Pedido" not in edge.from_node
            assert "Pedido" not in edge.to_node

        # Assert: embeddings gone
        assert store.read_embeddings("Pedido") == []

    def test_delete_nonexistent_is_noop(self, store):
        # Should not raise
        store.delete_document_artifacts("Missing")

    def test_preserves_other_documents(self, store, sample_node, sample_edges):
        other_node = GraphNode(
            id="CMD:CMD-001",
            kind=KDDKind.COMMAND,
            source_file="specs/02-behavior/commands/CMD-001.md",
            source_hash="def456",
            layer=KDDLayer.BEHAVIOR,
        )
        other_edge = GraphEdge(
            from_node="CMD:CMD-001",
            to_node="Event:EVT-X",
            edge_type="EMITS",
            source_file="specs/02-behavior/commands/CMD-001.md",
            extraction_method="wiki_link",
        )
        store.write_node(sample_node)
        store.write_node(other_node)
        store.append_edges(sample_edges + [other_edge])

        store.delete_document_artifacts("Pedido")

        # Other node untouched
        assert store.read_node("CMD:CMD-001") is not None
        # Other edge preserved
        remaining = store.read_edges()
        assert len(remaining) == 1
        assert remaining[0].from_node == "CMD:CMD-001"
