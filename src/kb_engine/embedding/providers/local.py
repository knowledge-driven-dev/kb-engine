"""Local embedding provider."""

from kb_engine.embedding.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local model-based embedding provider.

    Uses sentence-transformers or similar local models.
    """

    def __init__(
        self,
        model_path: str | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._model_path = model_path
        self._model_name = model_name
        self._model = None
        self._dimensions_cache: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        if self._dimensions_cache is None:
            # Default dimension for common models
            self._dimensions_cache = 384
        return self._dimensions_cache

    async def _ensure_model(self) -> None:
        """Ensure local model is loaded."""
        if self._model is None:
            # TODO: Load sentence-transformers model
            pass

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text using local model."""
        await self._ensure_model()
        # TODO: Implement local embedding
        raise NotImplementedError("LocalEmbeddingProvider.embed_text not implemented")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using local model."""
        await self._ensure_model()
        # TODO: Implement batch local embedding
        raise NotImplementedError("LocalEmbeddingProvider.embed_texts not implemented")
