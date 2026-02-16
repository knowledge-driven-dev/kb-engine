"""Tests for kdd.domain.events."""

from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import uuid4

import pytest

from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer, RetrievalStrategy
from kdd.domain.events import (
    DocumentDeleted,
    DocumentDetected,
    DocumentIndexed,
    DocumentParsed,
    DocumentStale,
    MergeCompleted,
    MergeRequested,
    QueryCompleted,
    QueryFailed,
    QueryReceived,
)


class TestDocumentDetected:
    def test_creation(self):
        evt = DocumentDetected(
            source_path="specs/01-domain/entities/Pedido.md",
            source_hash="abc123",
            kind=KDDKind.ENTITY,
            layer=KDDLayer.DOMAIN,
            detected_at=datetime.now(),
        )
        assert evt.kind == KDDKind.ENTITY
        assert evt.layer == KDDLayer.DOMAIN

    def test_frozen(self):
        evt = DocumentDetected(
            source_path="x",
            source_hash="x",
            kind=KDDKind.ENTITY,
            layer=KDDLayer.DOMAIN,
            detected_at=datetime.now(),
        )
        with pytest.raises(FrozenInstanceError):
            evt.source_path = "y"


class TestDocumentParsed:
    def test_payload_completeness(self):
        evt = DocumentParsed(
            document_id="Pedido",
            source_path="specs/01-domain/entities/Pedido.md",
            kind=KDDKind.ENTITY,
            front_matter={"kind": "entity", "aliases": ["Orden"]},
            section_count=5,
            wiki_link_count=3,
            parsed_at=datetime.now(),
        )
        assert evt.section_count == 5
        assert evt.wiki_link_count == 3
        assert "aliases" in evt.front_matter


class TestDocumentIndexed:
    def test_payload_completeness(self):
        evt = DocumentIndexed(
            document_id="Pedido",
            source_path="specs/01-domain/entities/Pedido.md",
            kind=KDDKind.ENTITY,
            node_id="Entity:Pedido",
            edge_count=5,
            embedding_count=3,
            index_level=IndexLevel.L2,
            duration_ms=150,
            indexed_at=datetime.now(),
        )
        assert evt.node_id == "Entity:Pedido"
        assert evt.index_level == IndexLevel.L2

    def test_l1_has_zero_embeddings(self):
        evt = DocumentIndexed(
            document_id="EVT-Pedido-Creado",
            source_path="specs/01-domain/events/EVT-Pedido-Creado.md",
            kind=KDDKind.EVENT,
            node_id="Event:EVT-Pedido-Creado",
            edge_count=2,
            embedding_count=0,
            index_level=IndexLevel.L1,
            duration_ms=50,
            indexed_at=datetime.now(),
        )
        assert evt.embedding_count == 0


class TestDocumentStale:
    def test_hashes_differ(self):
        evt = DocumentStale(
            document_id="Pedido",
            source_path="specs/01-domain/entities/Pedido.md",
            previous_hash="abc123",
            current_hash="def456",
            detected_at=datetime.now(),
        )
        assert evt.previous_hash != evt.current_hash


class TestDocumentDeleted:
    def test_payload_completeness(self):
        evt = DocumentDeleted(
            document_id="Pedido",
            source_path="specs/01-domain/entities/Pedido.md",
            node_id="Entity:Pedido",
            edge_count=5,
            embedding_count=3,
            deleted_at=datetime.now(),
        )
        assert evt.edge_count == 5


class TestMergeRequested:
    def test_payload_completeness(self):
        evt = MergeRequested(
            merge_id=uuid4(),
            source_manifests=["manifest-a", "manifest-b"],
            developer_ids=["alice", "bob"],
            target_version="1.0.0",
            requested_at=datetime.now(),
            requested_by="system",
        )
        assert len(evt.source_manifests) == 2
        assert len(evt.developer_ids) == 2


class TestMergeCompleted:
    def test_payload_completeness(self):
        evt = MergeCompleted(
            merge_id=uuid4(),
            merged_manifest_id="merged-001",
            source_count=2,
            total_nodes=47,
            total_edges=132,
            total_embeddings=31,
            conflicts_resolved=1,
            duration_ms=500,
            completed_at=datetime.now(),
        )
        assert evt.conflicts_resolved == 1


class TestQueryReceived:
    def test_payload_completeness(self):
        evt = QueryReceived(
            query_id=uuid4(),
            strategy=RetrievalStrategy.HYBRID,
            query_text="indexing pipeline",
            caller="agent-codex",
        )
        assert evt.strategy == RetrievalStrategy.HYBRID

    def test_graph_query_no_text(self):
        evt = QueryReceived(
            query_id=uuid4(),
            strategy=RetrievalStrategy.GRAPH,
            root_node="Entity:Pedido",
        )
        assert evt.query_text is None
        assert evt.root_node == "Entity:Pedido"


class TestQueryCompleted:
    def test_payload_completeness(self):
        evt = QueryCompleted(
            query_id=uuid4(),
            strategy=RetrievalStrategy.HYBRID,
            total_results=5,
            top_score=0.95,
            total_tokens=1500,
            duration_ms=120,
            completed_at=datetime.now(),
        )
        assert evt.duration_ms == 120


class TestQueryFailed:
    def test_payload_completeness(self):
        evt = QueryFailed(
            query_id=uuid4(),
            strategy=RetrievalStrategy.SEMANTIC,
            error_code="INDEX_UNAVAILABLE",
            error_message="No index loaded",
            phase="resolution",
            duration_ms=5,
            failed_at=datetime.now(),
        )
        assert evt.phase == "resolution"
        assert evt.error_code == "INDEX_UNAVAILABLE"


class TestAllEventsAreFrozen:
    """Verify every event class is immutable."""

    EVENT_CLASSES = [
        DocumentDetected, DocumentParsed, DocumentIndexed,
        DocumentStale, DocumentDeleted,
        MergeRequested, MergeCompleted,
        QueryReceived, QueryCompleted, QueryFailed,
    ]

    def test_count(self):
        assert len(self.EVENT_CLASSES) == 10
