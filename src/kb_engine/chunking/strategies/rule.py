"""Business rule chunking strategy."""

import re

from kb_engine.chunking.base import BaseChunkingStrategy
from kb_engine.core.models.document import Chunk, ChunkType, Document


class RuleChunkingStrategy(BaseChunkingStrategy):
    """Chunking strategy for business rules.

    Identifies and extracts chunks that define business rules,
    constraints, validations, or policies.
    """

    RULE_PATTERNS = [
        r"^#+\s*(?:regla|rule|rn[-_]?\d+|br[-_]?\d+)",
        r"(?:regla\s+de\s+negocio|business\s+rule)",
        r"(?:restricci[oó]n|constraint|validaci[oó]n|validation)",
        r"(?:cuando|when|si|if)\s+.*(?:entonces|then|debe|must|should)",
        r"(?:no\s+(?:se\s+)?permite|not\s+allowed|prohibited|forbidden)",
        r"(?:obligatorio|mandatory|required|requerido)",
        r"(?:pol[ií]tica|policy)\s*[:]\s*",
    ]

    @property
    def chunk_type(self) -> ChunkType:
        return ChunkType.RULE

    def can_handle(self, document: Document, section_content: str) -> bool:
        """Check if content appears to define a business rule."""
        content_lower = section_content.lower()

        for pattern in self.RULE_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                return True

        return False

    def chunk(
        self,
        document: Document,
        content: str,
        heading_path: list[str] | None = None,
    ) -> list[Chunk]:
        """Chunk business rule content.

        Business rules are typically atomic and should be kept intact.
        We only split if absolutely necessary due to size.
        """
        chunks = []

        # Try to identify individual rules
        rules = self._extract_individual_rules(content)

        if len(rules) <= 1:
            # Single rule or no clear structure
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
        else:
            # Multiple rules - chunk each separately
            for i, rule in enumerate(rules):
                if rule.strip():
                    chunks.append(
                        self._create_chunk(
                            document=document,
                            content=rule.strip(),
                            sequence=i,
                            heading_path=heading_path,
                        )
                    )

        return chunks

    def _extract_individual_rules(self, content: str) -> list[str]:
        """Extract individual rules from content."""
        # Look for numbered rules or bullet points
        rule_pattern = r"(?:^|\n)(?:\d+\.|[-*])\s*(?:RN[-_]?\d+|BR[-_]?\d+|Regla|Rule)?\s*[:\s]"

        parts = re.split(rule_pattern, content, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        # Try splitting by "when/if...then" patterns
        conditional_pattern = r"(?:^|\n\n)(?:cuando|when|si|if)\s+"
        parts = re.split(conditional_pattern, content, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        return [content]
