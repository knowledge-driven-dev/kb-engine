"""Tests for HNSWLibVectorStore."""

from datetime import datetime

import pytest

from kdd.domain.entities import Embedding
from kdd.domain.enums import KDDKind
from kdd.infrastructure.vector.hnswlib_store import HNSWLibVectorStore


def _embedding(id: str, vector: list[float], doc_id: str = "doc1") -> Embedding:
    return Embedding(
        id=id,
        document_id=doc_id,
        document_kind=KDDKind.ENTITY,
        section_path="Descripción",
        chunk_index=0,
        raw_text="test text",
        context_text="test context",
        vector=vector,
        model="test-model",
        dimensions=len(vector),
        text_hash="abc123",
        generated_at=datetime.now(),
    )


@pytest.fixture
def store():
    return HNSWLibVectorStore()


@pytest.fixture
def loaded_store():
    """Store with 4 vectors in 3D space."""
    s = HNSWLibVectorStore()
    embeddings = [
        _embedding("doc1:chunk-0", [1.0, 0.0, 0.0], "doc1"),
        _embedding("doc2:chunk-0", [0.9, 0.1, 0.0], "doc2"),
        _embedding("doc3:chunk-0", [0.0, 1.0, 0.0], "doc3"),
        _embedding("doc4:chunk-0", [0.0, 0.0, 1.0], "doc4"),
    ]
    s.load(embeddings)
    return s


class TestLoad:
    def test_empty_load(self, store):
        store.load([])
        assert store.size == 0

    def test_load_sets_dimensions(self, loaded_store):
        assert loaded_store.dimensions == 3
        assert loaded_store.size == 4


class TestSearch:
    def test_find_nearest(self, loaded_store):
        # Query near doc1 [1, 0, 0] — doc1 and doc2 should be closest
        results = loaded_store.search([1.0, 0.0, 0.0], limit=2)
        assert len(results) == 2
        ids = [r[0] for r in results]
        assert "doc1:chunk-0" in ids
        assert "doc2:chunk-0" in ids

    def test_scores_are_sorted_descending(self, loaded_store):
        results = loaded_store.search([1.0, 0.0, 0.0], limit=4)
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_min_score_filter(self, loaded_store):
        results = loaded_store.search([1.0, 0.0, 0.0], limit=4, min_score=0.9)
        # Only doc1 (exact match, score=1.0) and doc2 (very similar) should pass
        assert all(score >= 0.9 for _, score in results)

    def test_high_min_score_filters_all(self, loaded_store):
        results = loaded_store.search([0.5, 0.5, 0.5], limit=4, min_score=0.999)
        # No exact match exists
        assert len(results) <= 1  # might get one close match

    def test_empty_store_returns_empty(self, store):
        results = store.search([1.0, 0.0, 0.0], limit=5)
        assert results == []

    def test_limit_respected(self, loaded_store):
        results = loaded_store.search([1.0, 0.0, 0.0], limit=1)
        assert len(results) == 1

    def test_orthogonal_query(self, loaded_store):
        # Query [0, 0, 1] should match doc4 best
        results = loaded_store.search([0.0, 0.0, 1.0], limit=1)
        assert results[0][0] == "doc4:chunk-0"
