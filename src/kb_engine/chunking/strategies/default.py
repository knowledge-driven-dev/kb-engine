"""Default chunking strategy."""

from kb_engine.chunking.base import BaseChunkingStrategy
from kb_engine.core.models.document import Chunk, ChunkType, Document


class DefaultChunkingStrategy(BaseChunkingStrategy):
    """Default chunking strategy for generic content.

    Used when no specialized strategy matches the content.
    Applies general-purpose text chunking with overlap.
    """

    @property
    def chunk_type(self) -> ChunkType:
        return ChunkType.DEFAULT

    def can_handle(self, document: Document, section_content: str) -> bool:
        """Default strategy can handle any content."""
        return True

    def chunk(
        self,
        document: Document,
        content: str,
        heading_path: list[str] | None = None,
    ) -> list[Chunk]:
        """Chunk content using default size-based splitting."""
        chunks = []

        if len(content) <= self._config.max_chunk_size:
            # Content fits in a single chunk
            chunks.append(
                self._create_chunk(
                    document=document,
                    content=content,
                    sequence=0,
                    heading_path=heading_path,
                )
            )
        else:
            # Split content respecting size limits
            text_parts = self._split_by_size(content)
            for i, part in enumerate(text_parts):
                chunks.append(
                    self._create_chunk(
                        document=document,
                        content=part,
                        sequence=i,
                        heading_path=heading_path,
                    )
                )

        return chunks
