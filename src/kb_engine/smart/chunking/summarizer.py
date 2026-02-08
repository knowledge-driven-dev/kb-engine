"""Summary services for hierarchical chunking."""

from abc import ABC, abstractmethod

import structlog

from kb_engine.smart.types import ParsedDocument, ParsedSection

logger = structlog.get_logger(__name__)


class SummaryService(ABC):
    """Abstract base class for summary generation."""

    @abstractmethod
    async def summarize_document(self, parsed: ParsedDocument) -> str:
        """Generate a one-line summary of the document."""
        pass

    @abstractmethod
    async def summarize_section(self, section: ParsedSection, doc_context: str) -> str:
        """Generate a one-line summary of a section."""
        pass


class MockSummaryService(SummaryService):
    """Mock summary service for testing (no LLM calls)."""

    async def summarize_document(self, parsed: ParsedDocument) -> str:
        """Generate mock document summary."""
        return f"Doc: {parsed.title}"

    async def summarize_section(self, section: ParsedSection, doc_context: str) -> str:
        """Generate mock section summary."""
        return f"Sec: {section.name}"


class LLMSummaryService(SummaryService):
    """Summary service using OpenAI LLM."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        """Initialize LLM summary service.

        Args:
            model: OpenAI model to use.
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        """
        self.model = model
        self._client = None
        self._api_key = api_key

    @property
    def client(self):
        """Lazy initialize OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def summarize_document(self, parsed: ParsedDocument) -> str:
        """Generate document summary using LLM."""
        log = logger.bind(title=parsed.title)
        log.debug("summarizer.document.start")

        # Build a condensed view of the document
        content_preview = parsed.raw_content[:2000]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Genera un resumen de UNA SOLA LÍNEA (máximo 100 caracteres) del siguiente documento. El resumen debe capturar la esencia del documento de forma concisa."
                    },
                    {
                        "role": "user",
                        "content": f"Documento: {parsed.title}\n\n{content_preview}"
                    }
                ],
                max_tokens=50,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()
            log.debug("summarizer.document.complete", summary_length=len(summary))
            return summary

        except Exception as e:
            log.warning("summarizer.document.error", error=str(e))
            return f"Doc: {parsed.title}"

    async def summarize_section(self, section: ParsedSection, doc_context: str) -> str:
        """Generate section summary using LLM."""
        log = logger.bind(section=section.name)
        log.debug("summarizer.section.start")

        content_preview = section.content[:1000]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Genera un resumen de UNA SOLA LÍNEA (máximo 80 caracteres) de la siguiente sección de documento. El resumen debe ser conciso y capturar el propósito de la sección."
                    },
                    {
                        "role": "user",
                        "content": f"Contexto del documento: {doc_context}\n\nSección: {section.name}\n\n{content_preview}"
                    }
                ],
                max_tokens=40,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()
            log.debug("summarizer.section.complete", summary_length=len(summary))
            return summary

        except Exception as e:
            log.warning("summarizer.section.error", error=str(e))
            return f"Sec: {section.name}"
