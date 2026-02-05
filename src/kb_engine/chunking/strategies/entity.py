"""Entity chunking strategy."""

import re

from kb_engine.chunking.base import BaseChunkingStrategy
from kb_engine.core.models.document import Chunk, ChunkType, Document


class EntityChunkingStrategy(BaseChunkingStrategy):
    """Chunking strategy for entity definitions.

    Identifies and extracts chunks that define domain entities,
    their attributes, and relationships.
    """

    # Patterns that indicate entity definitions
    ENTITY_PATTERNS = [
        r"^#+\s*(?:entidad|entity|objeto|object)[\s:]+",
        r"(?:se\s+define|is\s+defined\s+as|represents?|describes?)\s+(?:una?|an?|the)\s+\w+",
        r"(?:atributos?|attributes?|propiedades?|properties?)[\s:]+",
        r"^[-*]\s*\*\*\w+\*\*\s*[:]\s*",  # Attribute definitions like "- **name**: description"
    ]

    @property
    def chunk_type(self) -> ChunkType:
        return ChunkType.ENTITY

    def can_handle(self, document: Document, section_content: str) -> bool:
        """Check if content appears to define an entity."""
        content_lower = section_content.lower()

        # Check heading path in document metadata or common patterns
        for pattern in self.ENTITY_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                return True

        # Check for attribute list pattern (common in entity definitions)
        attribute_lines = re.findall(r"^[-*]\s*\*\*\w+\*\*", section_content, re.MULTILINE)
        if len(attribute_lines) >= 3:
            return True

        return False

    def chunk(
        self,
        document: Document,
        content: str,
        heading_path: list[str] | None = None,
    ) -> list[Chunk]:
        """Chunk entity content.

        For entities, we try to keep the entire definition together
        if possible, including all attributes.
        """
        chunks = []

        # Try to keep entity definition intact
        if len(content) <= self._config.max_chunk_size:
            chunks.append(
                self._create_chunk(
                    document=document,
                    content=content,
                    sequence=0,
                    heading_path=heading_path,
                )
            )
        else:
            # Split large entity definitions
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
