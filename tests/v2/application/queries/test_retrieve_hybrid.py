"""Tests for QRY-003 RetrieveHybrid."""

import pytest

from kdd.application.queries.retrieve_hybrid import (
    HybridQueryInput,
    retrieve_hybrid,
)
from kdd.domain.enums import KDDKind


class FakeEmbeddingModel:
    """A fake embedding model that returns fixed vectors."""

    @property
    def model_name(self) -> str:
        return "test-model"

    @property
    def dimensions(self) -> int:
        return 8

    def encode(self, texts: list[str]) -> list[list[float]]:
        # Return a vector pointing toward doc1 (KDDDocument)
        return [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]] * len(texts)


class TestRetrieveHybrid:
    def test_basic_hybrid_search(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(query_text="KDDDocument indexing"),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        assert result.total_results > 0
        assert len(result.results) == result.total_results

    def test_fusion_scoring(self, graph_store, vector_store):
        """Nodes found via both semantic AND graph should score highest."""
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="KDDDocument",
                expand_graph=True,
                depth=1,
                min_score=0.1,
            ),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        # Find nodes with fusion match_source
        fusion_nodes = [r for r in result.results if r.match_source == "fusion"]
        non_fusion = [r for r in result.results if r.match_source != "fusion"]
        if fusion_nodes and non_fusion:
            assert fusion_nodes[0].score >= non_fusion[0].score

    def test_graph_expansion_edges(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="KDDDocument",
                expand_graph=True,
                depth=1,
                min_score=0.1,
            ),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        assert len(result.graph_expansion) > 0

    def test_no_graph_expansion(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="KDDDocument",
                expand_graph=False,
                min_score=0.1,
            ),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        assert result.graph_expansion == []

    def test_kind_filter(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="KDDDocument",
                include_kinds=[KDDKind.ENTITY],
                min_score=0.1,
            ),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        for r in result.results:
            node = graph_store.get_node(r.node_id)
            assert node.kind == KDDKind.ENTITY

    def test_degrades_without_vector_store(self, graph_store):
        """L1 mode: no vector store, should still return graph+lexical results."""
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="IndexDocument",
                min_score=0.1,
            ),
            graph_store,
            vector_store=None,
            embedding_model=None,
        )
        assert "NO_EMBEDDINGS" in result.warnings[0]
        # Should still find nodes via lexical search
        assert result.total_results > 0

    def test_limit_respected(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="KDDDocument",
                limit=2,
                min_score=0.1,
            ),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        assert result.total_results <= 2

    def test_query_too_short(self, graph_store):
        with pytest.raises(ValueError, match="QUERY_TOO_SHORT"):
            retrieve_hybrid(
                HybridQueryInput(query_text="ab"),
                graph_store,
            )

    def test_results_sorted_by_score(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(query_text="KDDDocument", min_score=0.1),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        scores = [r.score for r in result.results]
        assert scores == sorted(scores, reverse=True)

    def test_max_tokens_truncation(self, graph_store, vector_store):
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text="KDDDocument",
                max_tokens=5,
                min_score=0.1,
            ),
            graph_store,
            vector_store,
            FakeEmbeddingModel(),
        )
        # Should have fewer results due to token limit
        assert result.total_tokens <= 10  # some slack for estimation
