"""Process/workflow chunking strategy."""

import re

from kb_engine.chunking.base import BaseChunkingStrategy
from kb_engine.core.models.document import Chunk, ChunkType, Document


class ProcessChunkingStrategy(BaseChunkingStrategy):
    """Chunking strategy for process/workflow descriptions.

    Identifies and extracts chunks that describe processes,
    workflows, procedures, or sequences of steps.
    """

    PROCESS_PATTERNS = [
        r"^#+\s*(?:proceso|process|flujo|flow|workflow|procedimiento|procedure)",
        r"(?:diagrama\s+de\s+(?:flujo|actividad)|flow\s*chart|activity\s+diagram)",
        r"(?:paso(?:s)?|step(?:s)?)\s*(?:\d+|[:])?\s*",
        r"(?:secuencia|sequence)\s+(?:de|of)\s+",
        r"(?:primero|segundo|tercero|first|second|third|then|después|luego)",
        r"(?:\d+\.\s+|\d+\)\s+).*(?:\d+\.\s+|\d+\)\s+)",  # Numbered steps
    ]

    @property
    def chunk_type(self) -> ChunkType:
        return ChunkType.PROCESS

    def can_handle(self, document: Document, section_content: str) -> bool:
        """Check if content appears to describe a process."""
        content_lower = section_content.lower()

        for pattern in self.PROCESS_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                return True

        # Check for numbered lists (common in process descriptions)
        numbered_items = re.findall(r"^\s*\d+[\.\)]\s+", section_content, re.MULTILINE)
        if len(numbered_items) >= 3:
            return True

        return False

    def chunk(
        self,
        document: Document,
        content: str,
        heading_path: list[str] | None = None,
    ) -> list[Chunk]:
        """Chunk process content.

        Processes are sequential, so we try to preserve the order
        and context of steps while respecting size limits.
        """
        chunks = []

        # Try to keep the entire process together if possible
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
            # Split by logical groups of steps
            step_groups = self._group_steps(content)

            for i, group in enumerate(step_groups):
                if group.strip():
                    # Further split if still too large
                    if len(group) <= self._config.max_chunk_size:
                        chunks.append(
                            self._create_chunk(
                                document=document,
                                content=group.strip(),
                                sequence=len(chunks),
                                heading_path=heading_path,
                            )
                        )
                    else:
                        text_parts = self._split_by_size(group)
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

    def _group_steps(self, content: str) -> list[str]:
        """Group process steps into logical chunks."""
        # Find numbered steps
        step_pattern = r"(?:^|\n)(\s*\d+[\.\)]\s+)"
        matches = list(re.finditer(step_pattern, content))

        if not matches:
            # No numbered steps, try bullet points
            step_pattern = r"(?:^|\n)(\s*[-*]\s+)"
            matches = list(re.finditer(step_pattern, content))

        if not matches:
            return [content]

        # Group steps to fit within target size
        groups = []
        current_group_start = 0
        current_group_size = 0
        target_size = self._config.target_chunk_size

        for i, match in enumerate(matches):
            step_start = match.start()

            # Determine step content (until next step or end)
            if i + 1 < len(matches):
                step_end = matches[i + 1].start()
            else:
                step_end = len(content)

            step_size = step_end - step_start

            if current_group_size + step_size > target_size and current_group_size > 0:
                # Start a new group
                groups.append(content[current_group_start:step_start].strip())
                current_group_start = step_start
                current_group_size = step_size
            else:
                current_group_size += step_size

        # Add the last group
        if current_group_start < len(content):
            groups.append(content[current_group_start:].strip())

        return groups
