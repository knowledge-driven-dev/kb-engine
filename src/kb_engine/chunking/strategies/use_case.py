"""Use case chunking strategy."""

import re

from kb_engine.chunking.base import BaseChunkingStrategy
from kb_engine.core.models.document import Chunk, ChunkType, Document


class UseCaseChunkingStrategy(BaseChunkingStrategy):
    """Chunking strategy for use case descriptions.

    Identifies and extracts chunks that describe use cases,
    user stories, or functional requirements.
    """

    USE_CASE_PATTERNS = [
        r"^#+\s*(?:caso\s+de\s+uso|use\s+case|cu[-_]?\d+)",
        r"^#+\s*(?:historia\s+de\s+usuario|user\s+story|us[-_]?\d+)",
        r"(?:como|as\s+a)\s+(?:un|una|an?)\s+\w+.*(?:quiero|want|necesito|need)",
        r"(?:actor(?:es)?|actors?)\s*[:]\s*",
        r"(?:precondici[oó]n|precondition|postcondici[oó]n|postcondition)",
        r"(?:flujo\s+(?:principal|alternativo)|main\s+flow|alternative\s+flow)",
    ]

    @property
    def chunk_type(self) -> ChunkType:
        return ChunkType.USE_CASE

    def can_handle(self, document: Document, section_content: str) -> bool:
        """Check if content appears to describe a use case."""
        content_lower = section_content.lower()

        for pattern in self.USE_CASE_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                return True

        return False

    def chunk(
        self,
        document: Document,
        content: str,
        heading_path: list[str] | None = None,
    ) -> list[Chunk]:
        """Chunk use case content.

        Use cases have a specific structure (actors, preconditions,
        flows, postconditions) that we try to preserve.
        """
        chunks = []

        # Try to identify use case sections
        sections = self._split_use_case_sections(content)

        if len(sections) == 1 or sum(len(s) for s in sections) <= self._config.max_chunk_size:
            # Keep entire use case together if small enough
            chunks.append(
                self._create_chunk(
                    document=document,
                    content=content,
                    sequence=0,
                    heading_path=heading_path,
                )
            )
        else:
            # Split by sections
            for i, section in enumerate(sections):
                if section.strip():
                    text_parts = self._split_by_size(section)
                    for part in text_parts:
                        chunks.append(
                            self._create_chunk(
                                document=document,
                                content=part,
                                sequence=len(chunks),
                                heading_path=heading_path,
                            )
                        )

        return chunks

    def _split_use_case_sections(self, content: str) -> list[str]:
        """Split use case into its constituent sections."""
        section_patterns = [
            r"(?:^|\n)(?:actor(?:es)?|actors?)\s*[:\n]",
            r"(?:^|\n)(?:precondici[oó]n(?:es)?|preconditions?)\s*[:\n]",
            r"(?:^|\n)(?:flujo\s+principal|main\s+flow)\s*[:\n]",
            r"(?:^|\n)(?:flujo(?:s)?\s+alternativo(?:s)?|alternative\s+flow(?:s)?)\s*[:\n]",
            r"(?:^|\n)(?:postcondici[oó]n(?:es)?|postconditions?)\s*[:\n]",
        ]

        # Find all section boundaries
        boundaries = [0]
        for pattern in section_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                boundaries.append(match.start())
        boundaries.append(len(content))
        boundaries = sorted(set(boundaries))

        # Extract sections
        sections = []
        for i in range(len(boundaries) - 1):
            section = content[boundaries[i] : boundaries[i + 1]].strip()
            if section:
                sections.append(section)

        return sections if sections else [content]
