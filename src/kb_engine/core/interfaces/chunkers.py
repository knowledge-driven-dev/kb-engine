"""Chunking strategy protocol as defined in ADR-0002."""

from typing import Protocol

from kb_engine.core.models.document import Chunk, ChunkType, Document


class ChunkingStrategy(Protocol):
    """Protocol for chunking strategies.

    Different content types require different chunking approaches.
    Each strategy knows how to extract meaningful chunks from
    specific types of content.
    """

    @property
    def chunk_type(self) -> ChunkType:
        """The type of chunks this strategy produces."""
        ...

    def can_handle(self, document: Document, section_content: str) -> bool:
        """Check if this strategy can handle the given content.

        Args:
            document: The source document.
            section_content: The content of a section to potentially chunk.

        Returns:
            True if this strategy should handle this content.
        """
        ...

    def chunk(
        self,
        document: Document,
        content: str,
        heading_path: list[str] | None = None,
    ) -> list[Chunk]:
        """Chunk the content into semantic units.

        Args:
            document: The source document.
            content: The content to chunk.
            heading_path: The path of headings leading to this content.

        Returns:
            List of chunks extracted from the content.
        """
        ...
