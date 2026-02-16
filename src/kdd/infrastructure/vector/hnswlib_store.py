"""HNSWLib-based VectorStore implementation.

Loads embedding vectors into an hnswlib HNSW index for fast approximate
nearest-neighbor search.  Implements the ``VectorStore`` port.

Used for:
- QRY-002 RetrieveSemantic
- QRY-003 RetrieveHybrid (semantic phase)
"""

from __future__ import annotations

import numpy as np

from kdd.domain.entities import Embedding


class HNSWLibVectorStore:
    """In-memory vector index backed by hnswlib."""

    def __init__(self) -> None:
        self._index = None  # hnswlib.Index, created on load()
        self._id_map: list[str] = []  # positional index → embedding ID
        self._dimensions: int = 0

    # ------------------------------------------------------------------
    # VectorStore port interface
    # ------------------------------------------------------------------

    def load(self, embeddings: list[Embedding]) -> None:
        """Build an HNSW index from a list of Embedding entities."""
        import hnswlib

        if not embeddings:
            self._index = None
            self._id_map = []
            return

        self._dimensions = embeddings[0].dimensions
        n = len(embeddings)

        # Build index
        index = hnswlib.Index(space="cosine", dim=self._dimensions)
        # ef_construction and M tuned for small-medium indices (< 10k vectors)
        index.init_index(max_elements=max(n, 16), ef_construction=200, M=16)

        vectors = np.array(
            [emb.vector for emb in embeddings], dtype=np.float32
        )
        ids = np.arange(n, dtype=np.int64)
        index.add_items(vectors, ids)
        index.set_ef(50)  # query-time ef

        self._index = index
        self._id_map = [emb.id for emb in embeddings]

    def search(
        self,
        vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Find nearest embeddings.

        Returns list of ``(embedding_id, cosine_similarity_score)`` sorted
        by score descending.

        hnswlib returns *distances* in cosine space where
        ``distance = 1 - similarity``, so we convert to similarity.
        """
        if self._index is None or not self._id_map:
            return []

        k = min(limit, len(self._id_map))
        query = np.array([vector], dtype=np.float32)

        labels, distances = self._index.knn_query(query, k=k)

        results: list[tuple[str, float]] = []
        for label, dist in zip(labels[0], distances[0]):
            score = 1.0 - float(dist)
            if score < min_score:
                continue
            emb_id = self._id_map[int(label)]
            results.append((emb_id, score))

        # Sort by score descending (hnswlib returns sorted by distance asc
        # which is score desc, but filter may have changed order)
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of vectors in the index."""
        return len(self._id_map)

    @property
    def dimensions(self) -> int:
        return self._dimensions
