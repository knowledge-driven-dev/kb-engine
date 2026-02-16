"""Tests for CMD-001 IndexDocument command."""

from pathlib import Path

import pytest

from kdd.application.commands.index_document import IndexResult, index_document
from kdd.application.extractors.registry import create_default_registry
from kdd.domain.events import DocumentDetected, DocumentIndexed, DocumentParsed
from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore
from kdd.infrastructure.events.bus import InMemoryEventBus

# Root of the specs/ directory
SPECS_ROOT = Path(__file__).resolve().parents[4] / "specs"


@pytest.fixture
def artifact_store(tmp_path):
    return FilesystemArtifactStore(tmp_path / ".kdd-index")


@pytest.fixture
def registry():
    return create_default_registry()


@pytest.fixture
def event_bus():
    return InMemoryEventBus()


class TestIndexDocumentL1:
    """Test L1 indexing (no embeddings)."""

    def test_index_entity(self, artifact_store, registry):
        result = index_document(
            SPECS_ROOT / "01-domain" / "entities" / "KDDDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is True
        assert result.node_id == "Entity:KDDDocument"
        assert result.edge_count > 0
        assert result.embedding_count == 0

    def test_index_creates_node_file(self, artifact_store, registry):
        index_document(
            SPECS_ROOT / "01-domain" / "entities" / "KDDDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        node = artifact_store.read_node("Entity:KDDDocument")
        assert node is not None
        assert node.kind.value == "entity"

    def test_index_creates_edges(self, artifact_store, registry):
        index_document(
            SPECS_ROOT / "01-domain" / "entities" / "KDDDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        edges = artifact_store.read_edges()
        assert len(edges) > 0

    def test_index_event(self, artifact_store, registry):
        result = index_document(
            SPECS_ROOT / "01-domain" / "events" / "EVT-KDDDocument-Indexed.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is True
        assert result.node_id == "Event:EVT-KDDDocument-Indexed"

    def test_index_command(self, artifact_store, registry):
        result = index_document(
            SPECS_ROOT / "02-behavior" / "commands" / "CMD-001-IndexDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is True
        assert result.node_id == "CMD:CMD-001"

    def test_index_use_case(self, artifact_store, registry):
        result = index_document(
            SPECS_ROOT / "02-behavior" / "use-cases" / "UC-001-IndexDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is True
        assert result.node_id == "UC:UC-001"

    def test_index_prd(self, artifact_store, registry):
        result = index_document(
            SPECS_ROOT / "00-requirements" / "PRD-KBEngine.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is True
        assert result.node_id == "PRD:PRD-KBEngine"


class TestIndexDocumentSkips:
    """Test documents that should be skipped."""

    def test_nonexistent_file(self, artifact_store, registry):
        result = index_document(
            SPECS_ROOT / "nonexistent.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is False
        assert "File error" in result.skipped_reason

    def test_no_frontmatter(self, artifact_store, registry, tmp_path):
        md = tmp_path / "plain.md"
        md.write_text("# Just a plain markdown file\n\nNo front-matter here.\n")
        result = index_document(
            md,
            specs_root=tmp_path,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is False
        assert "kind" in result.skipped_reason.lower()

    def test_unknown_kind(self, artifact_store, registry, tmp_path):
        md = tmp_path / "unknown.md"
        md.write_text("---\nid: X-001\nkind: spaceship\n---\n\n# Spaceship\n")
        result = index_document(
            md,
            specs_root=tmp_path,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.success is False
        assert "kind" in result.skipped_reason.lower()


class TestIndexDocumentEvents:
    """Test domain event emission."""

    def test_emits_document_detected(self, artifact_store, registry, event_bus):
        events = []
        event_bus.subscribe(DocumentDetected, lambda e: events.append(e))

        index_document(
            SPECS_ROOT / "01-domain" / "entities" / "KDDDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
            event_bus=event_bus,
        )
        assert len(events) == 1
        assert events[0].kind.value == "entity"

    def test_emits_document_parsed(self, artifact_store, registry, event_bus):
        events = []
        event_bus.subscribe(DocumentParsed, lambda e: events.append(e))

        index_document(
            SPECS_ROOT / "01-domain" / "entities" / "KDDDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
            event_bus=event_bus,
        )
        assert len(events) == 1
        assert events[0].section_count > 0

    def test_emits_document_indexed(self, artifact_store, registry, event_bus):
        events = []
        event_bus.subscribe(DocumentIndexed, lambda e: events.append(e))

        index_document(
            SPECS_ROOT / "01-domain" / "entities" / "KDDDocument.md",
            specs_root=SPECS_ROOT,
            registry=registry,
            artifact_store=artifact_store,
            event_bus=event_bus,
        )
        assert len(events) == 1
        assert events[0].node_id == "Entity:KDDDocument"
        assert events[0].edge_count > 0
