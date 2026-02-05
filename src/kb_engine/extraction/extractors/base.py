"""Base extractor implementation."""

from abc import ABC, abstractmethod

from kb_engine.core.interfaces.extractors import EntityExtractor, ExtractionResult
from kb_engine.core.models.document import Chunk, Document


class BaseExtractor(EntityExtractor, ABC):
    """Base class for entity extractors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of this extractor."""
        ...

    @property
    @abstractmethod
    def priority(self) -> int:
        """Extraction priority (lower = higher priority)."""
        ...

    @abstractmethod
    def can_extract(self, chunk: Chunk, document: Document) -> bool:
        """Check if this extractor can process the given chunk."""
        ...

    @abstractmethod
    async def extract(
        self,
        chunk: Chunk,
        document: Document,
    ) -> ExtractionResult:
        """Extract entities and relationships from a chunk."""
        ...
