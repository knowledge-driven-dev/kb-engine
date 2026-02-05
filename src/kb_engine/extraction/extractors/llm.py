"""LLM-based entity extractor."""

from kb_engine.core.interfaces.extractors import ExtractionResult
from kb_engine.core.models.document import Chunk, Document
from kb_engine.extraction.extractors.base import BaseExtractor
from kb_engine.extraction.models import ExtractedEdge, ExtractedNode


class LLMExtractor(BaseExtractor):
    """Extracts entities using a Large Language Model.

    Uses structured prompts to extract entities and relationships
    that may not be captured by pattern-based extraction.
    """

    def __init__(
        self,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.0,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._client = None

    @property
    def name(self) -> str:
        return "llm"

    @property
    def priority(self) -> int:
        return 30  # Lower priority (runs last)

    def can_extract(self, chunk: Chunk, document: Document) -> bool:
        """Can extract from any chunk with sufficient content."""
        return bool(chunk.content and len(chunk.content) > 50)

    async def _ensure_client(self) -> None:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            # TODO: Initialize OpenAI client
            pass

    async def extract(
        self,
        chunk: Chunk,
        document: Document,
    ) -> ExtractionResult:
        """Extract entities using LLM.

        TODO: Implement LLM-based extraction using structured output.
        """
        await self._ensure_client()

        # Placeholder - actual implementation would call OpenAI API
        nodes: list[ExtractedNode] = []
        edges: list[ExtractedEdge] = []

        # TODO: Implement LLM extraction with prompts like:
        # - "Extract all entities (people, systems, concepts) from this text"
        # - "Extract all relationships between entities"
        # - Use structured output / function calling for reliable parsing

        return ExtractionResult(nodes=nodes, edges=edges)  # type: ignore

    def _build_extraction_prompt(self, chunk: Chunk, document: Document) -> str:
        """Build the prompt for entity extraction."""
        return f"""Extract entities and relationships from the following text.

Document: {document.title}
Domain: {document.domain or 'Unknown'}
Chunk Type: {chunk.chunk_type.value}

Text:
{chunk.content}

Extract:
1. Entities: actors, systems, concepts, processes, rules
2. Relationships: dependencies, references, implementations

Return as JSON with format:
{{
  "entities": [
    {{"name": "...", "type": "...", "description": "..."}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "type": "...", "description": "..."}}
  ]
}}
"""
