"""Embedding configuration."""

from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    # Provider selection
    provider: str = Field(default="openai", description="Embedding provider (openai, local)")

    # OpenAI settings
    openai_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )
    openai_dimensions: int = Field(
        default=1536, description="Embedding dimensions for OpenAI"
    )

    # Local model settings
    local_model_path: str | None = Field(
        default=None, description="Path to local embedding model"
    )

    # Batch settings
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size for embedding")

    class Config:
        frozen = True
