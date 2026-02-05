"""Tests for core domain models."""

import pytest
from uuid import uuid4

from kb_engine.core.models.document import Chunk, ChunkType, Document, DocumentStatus
from kb_engine.core.models.embedding import Embedding
from kb_engine.core.models.graph import Edge, EdgeType, Node, NodeType
from kb_engine.core.models.search import RetrievalMode, SearchFilters, SearchResult


@pytest.mark.unit
class TestDocument:
    """Tests for Document model."""

    def test_create_document(self) -> None:
        """Test creating a document with required fields."""
        doc = Document(title="Test", content="Test content")

        assert doc.title == "Test"
        assert doc.content == "Test content"
        assert doc.status == DocumentStatus.PENDING
        assert doc.id is not None

    def test_document_with_metadata(self) -> None:
        """Test document with metadata and tags."""
        doc = Document(
            title="Test",
            content="Content",
            domain="test-domain",
            tags=["tag1", "tag2"],
            metadata={"key": "value"},
        )

        assert doc.domain == "test-domain"
        assert doc.tags == ["tag1", "tag2"]
        assert doc.metadata == {"key": "value"}


@pytest.mark.unit
class TestChunk:
    """Tests for Chunk model."""

    def test_create_chunk(self) -> None:
        """Test creating a chunk."""
        doc_id = uuid4()
        chunk = Chunk(
            document_id=doc_id,
            content="Chunk content",
            chunk_type=ChunkType.ENTITY,
        )

        assert chunk.document_id == doc_id
        assert chunk.content == "Chunk content"
        assert chunk.chunk_type == ChunkType.ENTITY

    def test_chunk_with_heading_path(self) -> None:
        """Test chunk with heading path."""
        chunk = Chunk(
            document_id=uuid4(),
            content="Content",
            heading_path=["Section 1", "Subsection 1.1"],
        )

        assert chunk.heading_path == ["Section 1", "Subsection 1.1"]


@pytest.mark.unit
class TestEmbedding:
    """Tests for Embedding model."""

    def test_create_embedding(self) -> None:
        """Test creating an embedding."""
        chunk_id = uuid4()
        doc_id = uuid4()
        vector = [0.1] * 1536

        embedding = Embedding(
            chunk_id=chunk_id,
            document_id=doc_id,
            vector=vector,
            model="text-embedding-3-small",
            dimensions=1536,
        )

        assert embedding.chunk_id == chunk_id
        assert embedding.document_id == doc_id
        assert len(embedding.vector) == 1536
        assert embedding.model == "text-embedding-3-small"

    def test_embedding_payload(self) -> None:
        """Test embedding payload generation."""
        chunk_id = uuid4()
        doc_id = uuid4()

        embedding = Embedding(
            chunk_id=chunk_id,
            document_id=doc_id,
            vector=[0.1],
            model="test-model",
            dimensions=1,
            metadata={"key": "value"},
        )

        payload = embedding.payload

        assert payload["chunk_id"] == str(chunk_id)
        assert payload["document_id"] == str(doc_id)
        assert payload["model"] == "test-model"
        assert payload["key"] == "value"


@pytest.mark.unit
class TestNode:
    """Tests for Node model."""

    def test_create_node(self) -> None:
        """Test creating a node."""
        node = Node(
            name="TestEntity",
            node_type=NodeType.ENTITY,
            description="A test entity",
        )

        assert node.name == "TestEntity"
        assert node.node_type == NodeType.ENTITY
        assert node.description == "A test entity"

    def test_node_types(self) -> None:
        """Test all node types can be used."""
        for node_type in NodeType:
            node = Node(name="Test", node_type=node_type)
            assert node.node_type == node_type


@pytest.mark.unit
class TestEdge:
    """Tests for Edge model."""

    def test_create_edge(self) -> None:
        """Test creating an edge."""
        source_id = uuid4()
        target_id = uuid4()

        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=EdgeType.DEPENDS_ON,
        )

        assert edge.source_id == source_id
        assert edge.target_id == target_id
        assert edge.edge_type == EdgeType.DEPENDS_ON

    def test_edge_types(self) -> None:
        """Test all edge types can be used."""
        for edge_type in EdgeType:
            edge = Edge(
                source_id=uuid4(),
                target_id=uuid4(),
                edge_type=edge_type,
            )
            assert edge.edge_type == edge_type


@pytest.mark.unit
class TestSearchFilters:
    """Tests for SearchFilters model."""

    def test_empty_filters(self) -> None:
        """Test creating empty filters."""
        filters = SearchFilters()

        assert filters.document_ids is None
        assert filters.domains is None
        assert filters.tags is None

    def test_filters_with_values(self) -> None:
        """Test filters with values."""
        doc_id = uuid4()
        filters = SearchFilters(
            document_ids=[doc_id],
            domains=["domain1"],
            tags=["tag1"],
            max_hops=3,
        )

        assert filters.document_ids == [doc_id]
        assert filters.domains == ["domain1"]
        assert filters.tags == ["tag1"]
        assert filters.max_hops == 3


@pytest.mark.unit
class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self, sample_chunk: Chunk) -> None:
        """Test creating a search result."""
        result = SearchResult(
            chunk=sample_chunk,
            score=0.95,
            retrieval_mode=RetrievalMode.VECTOR,
        )

        assert result.chunk == sample_chunk
        assert result.score == 0.95
        assert result.retrieval_mode == RetrievalMode.VECTOR
