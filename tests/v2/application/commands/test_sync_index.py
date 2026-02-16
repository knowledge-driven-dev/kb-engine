"""Tests for CMD-005 SyncIndex and CMD-003 EnrichWithAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from kdd.application.commands.sync_index import SyncResult, sync_pull, sync_push
from kdd.domain.entities import GraphEdge, GraphNode, IndexManifest, IndexStats
from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer
from kdd.domain.ports import ArtifactStore, Transport


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeTransport:
    """Records push/pull calls."""

    def __init__(self, *, fail: bool = False):
        self.calls: list[tuple[str, ...]] = []
        self._fail = fail

    def push(self, index_path: str, remote: str) -> None:
        if self._fail:
            raise ConnectionError("network down")
        self.calls.append(("push", index_path, remote))

    def pull(self, remote: str, target_path: str) -> None:
        if self._fail:
            raise ConnectionError("network down")
        self.calls.append(("pull", remote, target_path))


class FakeArtifactStore:
    """Minimal ArtifactStore for sync tests."""

    def __init__(self, has_manifest: bool = True):
        self._has_manifest = has_manifest

    def read_manifest(self):
        if not self._has_manifest:
            return None
        from datetime import datetime
        return IndexManifest(
            version="1.0.0",
            kdd_version="1.0.0",
            indexed_at=datetime.now(),
            indexed_by="test",
            index_level=IndexLevel.L1,
            stats=IndexStats(nodes=5, edges=3),
        )

    # Required by Protocol (not used in sync tests)
    def write_manifest(self, m): ...
    def write_node(self, n): ...
    def read_node(self, nid): ...
    def append_edges(self, e): ...
    def read_edges(self): return []
    def write_embeddings(self, e): ...
    def read_embeddings(self, did): return []
    def read_all_nodes(self): return []
    def read_all_embeddings(self): return []
    def delete_document_artifacts(self, did): ...


# ---------------------------------------------------------------------------
# sync_push tests
# ---------------------------------------------------------------------------


class TestSyncPush:
    def test_push_success(self):
        transport = FakeTransport()
        store = FakeArtifactStore()
        result = sync_push(store, transport)

        assert result.success
        assert result.direction == "push"
        assert len(transport.calls) == 1
        assert transport.calls[0][0] == "push"

    def test_push_no_manifest(self):
        transport = FakeTransport()
        store = FakeArtifactStore(has_manifest=False)
        result = sync_push(store, transport)

        assert not result.success
        assert "NO_LOCAL_INDEX" in result.error

    def test_push_transport_error(self):
        transport = FakeTransport(fail=True)
        store = FakeArtifactStore()
        result = sync_push(store, transport)

        assert not result.success
        assert "TRANSPORT_ERROR" in result.error


# ---------------------------------------------------------------------------
# sync_pull tests
# ---------------------------------------------------------------------------


class TestSyncPull:
    def test_pull_success(self):
        transport = FakeTransport()
        result = sync_pull(transport)

        assert result.success
        assert result.direction == "pull"
        assert len(transport.calls) == 1
        assert transport.calls[0][0] == "pull"

    def test_pull_transport_error(self):
        transport = FakeTransport(fail=True)
        result = sync_pull(transport)

        assert not result.success
        assert "TRANSPORT_ERROR" in result.error


# ---------------------------------------------------------------------------
# EnrichWithAgent tests
# ---------------------------------------------------------------------------


class FakeAgentClient:
    """Returns a canned enrichment."""

    def enrich(self, node, context: str) -> dict:
        return {
            "summary": "Enriched summary",
            "implicit_relations": [
                {"target": "Entity:GraphNode", "type": "WIKI_LINK"},
            ],
        }


class FailingAgentClient:
    def enrich(self, node, context: str) -> dict:
        raise RuntimeError("Agent unreachable")


class InMemoryArtifactStore:
    """ArtifactStore that holds state in memory for test verification."""

    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self.root = "/tmp/test-index"

    def write_manifest(self, m): ...

    def read_manifest(self):
        return None

    def write_node(self, node: GraphNode):
        self._nodes[node.id] = node

    def read_node(self, node_id: str):
        return self._nodes.get(node_id)

    def append_edges(self, edges):
        self._edges.extend(edges)

    def read_edges(self):
        return list(self._edges)

    def write_embeddings(self, e): ...
    def read_embeddings(self, did): return []
    def read_all_nodes(self): return list(self._nodes.values())
    def read_all_embeddings(self): return []
    def delete_document_artifacts(self, did): ...


class TestEnrichWithAgent:
    def test_enrich_success(self, tmp_path):
        from kdd.application.commands.enrich_with_agent import enrich_with_agent

        # Setup: create a spec file and a node
        spec_file = tmp_path / "entity.md"
        spec_file.write_text("# Entity\nSome content", encoding="utf-8")

        store = InMemoryArtifactStore()
        node = GraphNode(
            id="Entity:Test",
            kind=KDDKind.ENTITY,
            source_file="entity.md",
            source_hash="abc",
            layer=KDDLayer.DOMAIN,
        )
        store.write_node(node)

        result = enrich_with_agent(
            "Entity:Test",
            artifact_store=store,
            agent_client=FakeAgentClient(),
            specs_root=tmp_path,
        )

        assert result.success
        assert result.enrichment is not None
        assert result.implicit_edges == 1
        assert len(store._edges) == 1
        assert store._edges[0].extraction_method == "implicit"

    def test_enrich_node_not_found(self, tmp_path):
        from kdd.application.commands.enrich_with_agent import enrich_with_agent

        store = InMemoryArtifactStore()

        result = enrich_with_agent(
            "Entity:Missing",
            artifact_store=store,
            agent_client=FakeAgentClient(),
            specs_root=tmp_path,
        )

        assert not result.success
        assert "NODE_NOT_FOUND" in result.error

    def test_enrich_agent_error(self, tmp_path):
        from kdd.application.commands.enrich_with_agent import enrich_with_agent

        spec_file = tmp_path / "entity.md"
        spec_file.write_text("# Entity\nContent", encoding="utf-8")

        store = InMemoryArtifactStore()
        node = GraphNode(
            id="Entity:Test",
            kind=KDDKind.ENTITY,
            source_file="entity.md",
            source_hash="abc",
            layer=KDDLayer.DOMAIN,
        )
        store.write_node(node)

        result = enrich_with_agent(
            "Entity:Test",
            artifact_store=store,
            agent_client=FailingAgentClient(),
            specs_root=tmp_path,
        )

        assert not result.success
        assert "AGENT_ERROR" in result.error

    def test_enrich_document_missing(self, tmp_path):
        from kdd.application.commands.enrich_with_agent import enrich_with_agent

        store = InMemoryArtifactStore()
        node = GraphNode(
            id="Entity:Test",
            kind=KDDKind.ENTITY,
            source_file="does_not_exist.md",
            source_hash="abc",
            layer=KDDLayer.DOMAIN,
        )
        store.write_node(node)

        result = enrich_with_agent(
            "Entity:Test",
            artifact_store=store,
            agent_client=FakeAgentClient(),
            specs_root=tmp_path,
        )

        assert not result.success
        assert "DOCUMENT_NOT_FOUND" in result.error
