"""Embedding model."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Embedding(BaseModel):
    """A vector embedding for a chunk.

    Embeddings are stored in the vector store (Qdrant) and used
    for semantic similarity search.
    """

    id: UUID = Field(default_factory=uuid4)
    chunk_id: UUID
    document_id: UUID

    # Vector data
    vector: list[float]
    model: str
    dimensions: int

    # Metadata for filtering
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = False

    @property
    def payload(self) -> dict[str, str | int | float | bool]:
        """Get the payload for vector store."""
        return {
            "chunk_id": str(self.chunk_id),
            "document_id": str(self.document_id),
            "model": self.model,
            **self.metadata,
        }
