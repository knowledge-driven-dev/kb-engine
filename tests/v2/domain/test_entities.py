"""Tests for kdd.domain.entities."""

import pytest
from datetime import datetime
from uuid import uuid4

from kdd.domain.enums import (
    DocumentStatus,
    IndexLevel,
    KDDKind,
    KDDLayer,
    QueryStatus,
    RetrievalStrategy,
)
from kdd.domain.entities import (
    Embedding,
    GraphEdge,
    GraphNode,
    IndexManifest,
    IndexStats,
    KDDDocument,
    LayerViolation,
    RetrievalQuery,
    RetrievalResult,
    ScoredNode,
    Section,
)


class TestSection:
    def test_construction(self):
        s = Section(heading="Descripción", level=2, content="Some text")
        assert s.heading == "Descripción"
        assert s.level == 2
        assert s.path == ""

    def test_with_path(self):
        s = Section(heading="Atributos", level=2, content="...", path="descripcion.atributos")
        assert s.path == "descripcion.atributos"


class TestKDDDocument:
    def test_minimal_construction(self):
        doc = KDDDocument(
            id="Pedido",
            kind=KDDKind.ENTITY,
            source_path="specs/01-domain/entities/Pedido.md",
            source_hash="abc123",
            layer=KDDLayer.DOMAIN,
            front_matter={"kind": "entity"},
            sections=[],
        )
        assert doc.id == "Pedido"
        assert doc.kind == KDDKind.ENTITY
        assert doc.status == DocumentStatus.DETECTED
        assert doc.wiki_links == []
        assert doc.indexed_at is None
        assert doc.domain is None

    def test_with_all_fields(self):
        now = datetime.now()
        doc = KDDDocument(
            id="Pedido",
            kind=KDDKind.ENTITY,
            source_path="specs/01-domain/entities/Pedido.md",
            source_hash="abc123",
            layer=KDDLayer.DOMAIN,
            front_matter={"kind": "entity", "aliases": ["Orden"]},
            sections=[Section(heading="Desc", level=2, content="text")],
            wiki_links=["Usuario", "LineaPedido"],
            status=DocumentStatus.INDEXED,
            indexed_at=now,
            domain="core",
        )
        assert len(doc.wiki_links) == 2
        assert doc.status == DocumentStatus.INDEXED
        assert doc.domain == "core"

    def test_kind_must_be_valid(self):
        with pytest.raises(ValueError):
            KDDDocument(
                id="x",
                kind="invalid-kind",
                source_path="x",
                source_hash="x",
                layer=KDDLayer.DOMAIN,
                front_matter={},
                sections=[],
            )


class TestGraphNode:
    def test_construction(self):
        node = GraphNode(
            id="Entity:Pedido",
            kind=KDDKind.ENTITY,
            source_file="specs/01-domain/entities/Pedido.md",
            source_hash="abc123",
            layer=KDDLayer.DOMAIN,
        )
        assert node.id == "Entity:Pedido"
        assert node.status == "draft"
        assert node.aliases == []
        assert node.indexed_fields == {}

    def test_with_indexed_fields(self):
        node = GraphNode(
            id="Entity:Pedido",
            kind=KDDKind.ENTITY,
            source_file="specs/01-domain/entities/Pedido.md",
            source_hash="abc123",
            layer=KDDLayer.DOMAIN,
            indexed_fields={
                "description": "Represents an order",
                "attributes": [{"name": "id", "type": "uuid"}],
            },
        )
        assert "description" in node.indexed_fields
        assert len(node.indexed_fields["attributes"]) == 1


class TestGraphEdge:
    def test_structural_edge(self):
        edge = GraphEdge(
            from_node="UC:UC-001",
            to_node="Entity:KDDDocument",
            edge_type="WIKI_LINK",
            source_file="specs/02-behavior/use-cases/UC-001.md",
            extraction_method="wiki_link",
        )
        assert edge.layer_violation is False
        assert edge.bidirectional is False
        assert edge.metadata == {}

    def test_business_edge(self):
        edge = GraphEdge(
            from_node="Entity:Pedido",
            to_node="Entity:Usuario",
            edge_type="pertenece_a",
            source_file="specs/01-domain/entities/Pedido.md",
            extraction_method="section_content",
            metadata={"cardinality": "N:1"},
        )
        assert edge.edge_type == "pertenece_a"
        assert edge.metadata["cardinality"] == "N:1"

    def test_layer_violation_flag(self):
        edge = GraphEdge(
            from_node="Entity:X",
            to_node="UC:UC-001",
            edge_type="WIKI_LINK",
            source_file="specs/01-domain/entities/X.md",
            extraction_method="wiki_link",
            layer_violation=True,
        )
        assert edge.layer_violation is True


class TestEmbedding:
    def test_construction(self):
        emb = Embedding(
            id="Pedido:descripcion:0",
            document_id="Pedido",
            document_kind=KDDKind.ENTITY,
            section_path="descripcion",
            chunk_index=0,
            raw_text="An order placed by a user",
            context_text="[entity: Pedido] > [Descripción] > An order placed by a user",
            vector=[0.1] * 768,
            model="nomic-embed-text-v1.5",
            dimensions=768,
            text_hash="hash123",
            generated_at=datetime.now(),
        )
        assert emb.id == "Pedido:descripcion:0"
        assert len(emb.vector) == 768
        assert emb.dimensions == 768


class TestIndexManifest:
    def test_l1_manifest(self):
        m = IndexManifest(
            version="1.0.0",
            kdd_version="1.0",
            indexed_at=datetime.now(),
            indexed_by="dev-alice",
            index_level=IndexLevel.L1,
        )
        assert m.embedding_model is None
        assert m.embedding_dimensions is None
        assert m.stats.nodes == 0
        assert m.structure == "single-domain"

    def test_l2_manifest(self):
        m = IndexManifest(
            version="1.0.0",
            kdd_version="1.0",
            embedding_model="nomic-embed-text-v1.5",
            embedding_dimensions=768,
            indexed_at=datetime.now(),
            indexed_by="dev-bob",
            index_level=IndexLevel.L2,
            stats=IndexStats(nodes=47, edges=132, embeddings=31),
        )
        assert m.embedding_model == "nomic-embed-text-v1.5"
        assert m.stats.embeddings == 31

    def test_multi_domain(self):
        m = IndexManifest(
            version="1.0.0",
            kdd_version="1.0",
            indexed_at=datetime.now(),
            indexed_by="dev-alice",
            index_level=IndexLevel.L1,
            structure="multi-domain",
            domains=["core", "auth"],
        )
        assert m.structure == "multi-domain"
        assert len(m.domains) == 2


class TestRetrievalQuery:
    def test_hybrid_query(self):
        q = RetrievalQuery(
            id=uuid4(),
            strategy=RetrievalStrategy.HYBRID,
            query_text="indexing pipeline",
            received_at=datetime.now(),
        )
        assert q.depth == 2
        assert q.min_score == 0.7
        assert q.limit == 10
        assert q.max_tokens == 8000
        assert q.respect_layers is True
        assert q.status == QueryStatus.RECEIVED

    def test_graph_query(self):
        q = RetrievalQuery(
            id=uuid4(),
            strategy=RetrievalStrategy.GRAPH,
            root_node="Entity:Pedido",
            depth=3,
            edge_types=["EMITS", "DOMAIN_RELATION"],
            received_at=datetime.now(),
        )
        assert q.root_node == "Entity:Pedido"
        assert len(q.edge_types) == 2
        assert q.query_text is None


class TestRetrievalResult:
    def test_construction(self):
        qid = uuid4()
        r = RetrievalResult(
            query_id=qid,
            strategy=RetrievalStrategy.HYBRID,
            results=[
                ScoredNode(node_id="Entity:Pedido", score=0.95, match_source="fusion"),
                ScoredNode(node_id="UC:UC-001", score=0.82, match_source="semantic"),
            ],
            total_nodes=2,
            total_tokens=1500,
        )
        assert r.total_nodes == 2
        assert r.results[0].score > r.results[1].score
        assert r.layer_violations == []

    def test_with_violations(self):
        r = RetrievalResult(
            query_id=uuid4(),
            strategy=RetrievalStrategy.GRAPH,
            results=[],
            total_nodes=0,
            layer_violations=[
                LayerViolation(
                    from_node="Entity:X",
                    to_node="UC:UC-001",
                    from_layer=KDDLayer.DOMAIN,
                    to_layer=KDDLayer.BEHAVIOR,
                    edge_type="WIKI_LINK",
                ),
            ],
        )
        assert len(r.layer_violations) == 1
