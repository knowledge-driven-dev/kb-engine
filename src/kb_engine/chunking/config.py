"""Chunking configuration."""

from pydantic import BaseModel, Field


class ChunkingConfig(BaseModel):
    """Configuration for the chunking process.

    These values follow the recommendations in ADR-0002 for
    semantic chunking of KDD documents.
    """

    # Size constraints
    min_chunk_size: int = Field(default=100, ge=50, description="Minimum chunk size in tokens")
    target_chunk_size: int = Field(
        default=512, ge=100, description="Target chunk size in tokens"
    )
    max_chunk_size: int = Field(default=1024, ge=200, description="Maximum chunk size in tokens")
    overlap_size: int = Field(default=50, ge=0, description="Overlap between chunks in tokens")

    # Behavior
    preserve_sentences: bool = Field(
        default=True, description="Avoid splitting in the middle of sentences"
    )
    respect_headings: bool = Field(
        default=True, description="Use markdown headings as chunk boundaries"
    )
    include_heading_context: bool = Field(
        default=True, description="Include heading hierarchy in chunk metadata"
    )

    # Strategy selection
    enable_semantic_chunking: bool = Field(
        default=True, description="Enable semantic chunk type detection"
    )
    default_strategy: str = Field(
        default="default", description="Default chunking strategy to use"
    )

    class Config:
        frozen = True
