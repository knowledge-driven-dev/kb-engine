"""Sentence-transformers based EmbeddingModel implementation.

Wraps a HuggingFace sentence-transformers model for local L2 embedding
generation.  Implements the ``EmbeddingModel`` port.
"""

from __future__ import annotations


class SentenceTransformerModel:
    """Local embedding model using sentence-transformers."""

    def __init__(self, model_name: str = "all-mpnet-base-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        self._dimensions = self._model.get_sentence_embedding_dimension()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]
