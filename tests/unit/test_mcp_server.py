"""Tests for MCP server tools."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from kb_engine.core.models.document import Chunk, ChunkType, Document, DocumentStatus
from kb_engine.core.models.graph import Edge, EdgeType, Node, NodeType
from kb_engine.core.models.search import DocumentReference, RetrievalResponse


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _reset_services():
    """Reset global service state between tests."""
    import kb_engine.mcp_server as mod

    mod._retrieval_service = None
    mod._graph_repo = None
    mod._traceability_repo = None
    mod._factory = None
    yield
    mod._retrieval_service = None
    mod._graph_repo = None
    mod._traceability_repo = None
    mod._factory = None


@pytest.fixture
def mock_retrieval_service():
    return AsyncMock()


@pytest.fixture
def mock_graph_repo():
    return AsyncMock()


@pytest.fixture
def mock_traceability_repo():
    return AsyncMock()


def _patch_services(retrieval, graph, traceability):
    """Patch _get_services to return our mocks."""
    import kb_engine.mcp_server as mod

    mod._retrieval_service = retrieval
    mod._graph_repo = graph
    mod._traceability_repo = traceability


def _make_doc(**kwargs):
    defaults = {
        "id": uuid4(),
        "title": "Test Document",
        "content": "Some content",
        "source_path": "/repo/docs/test.md",
        "relative_path": "docs/test.md",
        "domain": "testing",
        "status": DocumentStatus.INDEXED,
        "metadata": {},
        "indexed_at": datetime(2025, 1, 15, 10, 30),
    }
    defaults.update(kwargs)
    return Document(**defaults)


def _make_ref(**kwargs):
    defaults = {
        "url": "file:///repo/docs/test.md#section",
        "document_path": "docs/test.md",
        "title": "Test Document",
        "section_title": "Introduction",
        "score": 0.87654,
        "snippet": "This is a test snippet with some content.",
        "chunk_type": "paragraph",
        "domain": "testing",
    }
    defaults.update(kwargs)
    return DocumentReference(**defaults)


# --- kdd_search tests ---


@pytest.mark.unit
class TestKddSearch:
    @pytest.mark.asyncio
    async def test_basic_search(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        mock_retrieval_service.search.return_value = RetrievalResponse(
            query="security model",
            references=[_make_ref(), _make_ref(title="Second", score=0.75)],
            total_count=2,
            processing_time_ms=42.0,
        )

        from kb_engine.mcp_server import kdd_search

        result = await kdd_search(query="security model", limit=5)
        data = json.loads(result)

        assert data["query"] == "security model"
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["score"] == 0.8765
        assert data["results"][0]["title"] == "Test Document"
        assert data["results"][0]["url"] == "file:///repo/docs/test.md#section"

        mock_retrieval_service.search.assert_awaited_once()
        call_kwargs = mock_retrieval_service.search.call_args.kwargs
        assert call_kwargs["query"] == "security model"
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        mock_retrieval_service.search.return_value = RetrievalResponse(
            query="test", references=[], total_count=0,
        )

        from kb_engine.mcp_server import kdd_search

        await kdd_search(
            query="test",
            chunk_types=["header"],
            domains=["architecture"],
            tags=["adr"],
            score_threshold=0.5,
        )

        call_kwargs = mock_retrieval_service.search.call_args.kwargs
        assert call_kwargs["filters"] is not None
        assert call_kwargs["filters"].chunk_types == ["header"]
        assert call_kwargs["filters"].domains == ["architecture"]
        assert call_kwargs["filters"].tags == ["adr"]
        assert call_kwargs["score_threshold"] == 0.5

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        mock_retrieval_service.search.return_value = RetrievalResponse(
            query="nonexistent", references=[], total_count=0,
        )

        from kb_engine.mcp_server import kdd_search

        result = await kdd_search(query="nonexistent")
        data = json.loads(result)

        assert data["total"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_result_structure(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        mock_retrieval_service.search.return_value = RetrievalResponse(
            query="q",
            references=[_make_ref()],
            total_count=1,
        )

        from kb_engine.mcp_server import kdd_search

        result = await kdd_search(query="q")
        data = json.loads(result)
        item = data["results"][0]

        expected_keys = {"url", "title", "section", "score", "snippet", "type", "domain", "retrieval_mode"}
        assert set(item.keys()) == expected_keys
        assert item["section"] == "Introduction"
        assert item["type"] == "paragraph"
        assert item["domain"] == "testing"


# --- kdd_related tests ---


@pytest.mark.unit
class TestKddRelated:
    @pytest.mark.asyncio
    async def test_related_entities(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        doc = _make_doc()
        start_node = Node(name="SecurityModel", node_type=NodeType.CONCEPT)
        target_node = Node(
            name="AuthModule",
            node_type=NodeType.ENTITY,
            source_document_id=doc.id,
        )
        edge = Edge(
            source_id=start_node.id,
            target_id=target_node.id,
            edge_type=EdgeType.REFERENCES,
        )

        mock_graph_repo.find_nodes.return_value = [start_node]
        mock_graph_repo.traverse.return_value = [(start_node, edge, target_node)]
        mock_traceability_repo.get_document.return_value = doc

        from kb_engine.mcp_server import kdd_related

        result = await kdd_related(entity="SecurityModel", depth=1)
        data = json.loads(result)

        assert data["entity"]["name"] == "SecurityModel"
        assert len(data["related"]) == 1
        assert data["related"][0]["name"] == "AuthModule"
        assert data["related"][0]["relationship"] == "REFERENCES"
        assert data["related"][0]["document_url"] == f"file://{doc.source_path}"

        mock_graph_repo.find_nodes.assert_awaited_once_with(name_pattern="SecurityModel")
        mock_graph_repo.traverse.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_related_no_graph(self, mock_retrieval_service, mock_traceability_repo):
        _patch_services(mock_retrieval_service, None, mock_traceability_repo)

        from kb_engine.mcp_server import kdd_related

        result = await kdd_related(entity="Something")
        data = json.loads(result)

        assert "error" in data
        assert "not available" in data["error"]

    @pytest.mark.asyncio
    async def test_related_entity_not_found(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        mock_graph_repo.find_nodes.return_value = []

        from kb_engine.mcp_server import kdd_related

        result = await kdd_related(entity="NonExistent")
        data = json.loads(result)

        assert data["related"] == []
        assert "No entity found" in data["message"]

    @pytest.mark.asyncio
    async def test_related_deduplicates_targets(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        start = Node(name="A", node_type=NodeType.CONCEPT)
        target = Node(name="B", node_type=NodeType.ENTITY)
        edge1 = Edge(source_id=start.id, target_id=target.id, edge_type=EdgeType.REFERENCES)
        edge2 = Edge(source_id=start.id, target_id=target.id, edge_type=EdgeType.CONTAINS)

        mock_graph_repo.find_nodes.return_value = [start]
        mock_graph_repo.traverse.return_value = [(start, edge1, target), (start, edge2, target)]
        mock_traceability_repo.get_document.return_value = None

        from kb_engine.mcp_server import kdd_related

        result = await kdd_related(entity="A")
        data = json.loads(result)

        assert len(data["related"]) == 1


# --- kdd_list tests ---


@pytest.mark.unit
class TestKddList:
    @pytest.mark.asyncio
    async def test_list_documents(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        doc = _make_doc()
        chunks = [
            Chunk(document_id=doc.id, content="chunk 1"),
            Chunk(document_id=doc.id, content="chunk 2"),
        ]

        mock_traceability_repo.list_documents.return_value = [doc]
        mock_traceability_repo.get_chunks_by_document.return_value = chunks

        from kb_engine.mcp_server import kdd_list

        result = await kdd_list()
        data = json.loads(result)

        assert data["total"] == 1
        item = data["documents"][0]
        assert item["path"] == "docs/test.md"
        assert item["title"] == "Test Document"
        assert item["status"] == "indexed"
        assert item["chunks"] == 2
        assert item["indexed_at"] is not None

    @pytest.mark.asyncio
    async def test_list_filter_by_kind(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        doc_adr = _make_doc(title="ADR-001", metadata={"kind": "adr"})
        doc_challenge = _make_doc(title="DC-001", metadata={"kind": "challenge"})

        mock_traceability_repo.list_documents.return_value = [doc_adr, doc_challenge]
        mock_traceability_repo.get_chunks_by_document.return_value = []

        from kb_engine.mcp_server import kdd_list

        result = await kdd_list(kind="adr")
        data = json.loads(result)

        assert data["total"] == 1
        assert data["documents"][0]["title"] == "ADR-001"
        assert data["documents"][0]["kind"] == "adr"

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        doc_indexed = _make_doc(status=DocumentStatus.INDEXED)
        doc_pending = _make_doc(title="Pending", status=DocumentStatus.PENDING)

        mock_traceability_repo.list_documents.return_value = [doc_indexed, doc_pending]
        mock_traceability_repo.get_chunks_by_document.return_value = []

        from kb_engine.mcp_server import kdd_list

        result = await kdd_list(status="indexed")
        data = json.loads(result)

        assert data["total"] == 1
        assert data["documents"][0]["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_list_filter_by_domain(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        mock_traceability_repo.list_documents.return_value = []

        from kb_engine.mcp_server import kdd_list

        await kdd_list(domain="architecture")

        call_kwargs = mock_traceability_repo.list_documents.call_args.kwargs
        assert call_kwargs["filters"].domains == ["architecture"]

    @pytest.mark.asyncio
    async def test_list_result_structure(self, mock_retrieval_service, mock_graph_repo, mock_traceability_repo):
        _patch_services(mock_retrieval_service, mock_graph_repo, mock_traceability_repo)

        doc = _make_doc(metadata={"kind": "adr"})
        mock_traceability_repo.list_documents.return_value = [doc]
        mock_traceability_repo.get_chunks_by_document.return_value = []

        from kb_engine.mcp_server import kdd_list

        result = await kdd_list()
        data = json.loads(result)
        item = data["documents"][0]

        expected_keys = {"path", "title", "kind", "domain", "status", "chunks", "indexed_at"}
        assert set(item.keys()) == expected_keys
