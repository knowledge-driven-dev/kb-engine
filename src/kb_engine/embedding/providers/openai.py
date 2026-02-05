"""OpenAI embedding provider."""

from kb_engine.embedding.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-based embedding provider."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._api_key = api_key
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _ensure_client(self) -> None:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            # TODO: Initialize OpenAI async client
            pass

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text using OpenAI."""
        await self._ensure_client()
        # TODO: Implement OpenAI embedding
        raise NotImplementedError("OpenAIEmbeddingProvider.embed_text not implemented")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using OpenAI."""
        await self._ensure_client()
        # TODO: Implement batch OpenAI embedding
        raise NotImplementedError("OpenAIEmbeddingProvider.embed_texts not implemented")
