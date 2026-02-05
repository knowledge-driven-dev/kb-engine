"""Base embedding provider."""

from abc import ABC, abstractmethod

from kb_engine.core.models.document import Chunk
from kb_engine.core.models.embedding import Embedding


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The name of the embedding model."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """The dimensionality of the embeddings."""
        ...

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...

    async def embed_chunk(self, chunk: Chunk) -> Embedding:
        """Generate embedding for a chunk."""
        vector = await self.embed_text(chunk.content)
        return Embedding(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            vector=vector,
            model=self.model_name,
            dimensions=self.dimensions,
            metadata={
                "chunk_type": chunk.chunk_type.value,
            },
        )

    async def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        """Generate embeddings for multiple chunks."""
        texts = [c.content for c in chunks]
        vectors = await self.embed_texts(texts)

        embeddings = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            embeddings.append(
                Embedding(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    vector=vector,
                    model=self.model_name,
                    dimensions=self.dimensions,
                    metadata={
                        "chunk_type": chunk.chunk_type.value,
                    },
                )
            )

        return embeddings
