"""Tests for HierarchicalChunker paragraph splitting (BR-EMBEDDING-001)."""

import pytest

from kb_engine.smart.chunking import HierarchicalChunker, MockSummaryService
from kb_engine.smart.types import (
    ChunkingStrategy,
    ContentExpectation,
    KDDDocumentKind,
    ParsedDocument,
    ParsedSection,
    SectionDefinition,
    TemplateSchema,
)

# Reusable paragraphs with >= 20 words each
P_PEDIDO = (
    "Representa un pedido de compra realizado por un Usuario registrado "
    "en la plataforma de comercio electrónico del sistema principal de ventas."
)  # 21 words
P_CICLO = (
    "El pedido tiene un ciclo de vida completo que va desde borrador hasta "
    "entregado, pasando por confirmado, en preparación y finalmente enviado."
)  # 22 words
P_LINEAS = (
    "Cada pedido contiene una o más líneas con productos seleccionados "
    "del catálogo vigente, incluyendo cantidades y precios unitarios actualizados al momento."
)  # 21 words


def _make_schema(
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SPLIT_BY_PARAGRAPHS,
    section_name: str = "Descripción",
) -> TemplateSchema:
    return TemplateSchema(
        kind=KDDDocumentKind.ENTITY,
        required_sections=[
            SectionDefinition(
                name=section_name,
                required=True,
                content_expectation=ContentExpectation.TEXT,
                chunking_strategy=chunking_strategy,
            ),
        ],
    )


def _make_parsed(
    content: str,
    section_name: str = "Descripción",
    doc_id: str = "TEST-001",
) -> ParsedDocument:
    return ParsedDocument(
        kind=KDDDocumentKind.ENTITY,
        frontmatter={"id": doc_id},
        title="TestEntity",
        sections=[
            ParsedSection(
                name=section_name,
                level=2,
                content=content,
            ),
        ],
        tables=[],
        code_blocks=[],
        cross_references=[],
        validation_errors=[],
        raw_content=content,
    )


def _make_chunker(max_chunk_size: int = 1024) -> HierarchicalChunker:
    return HierarchicalChunker(
        summary_service=MockSummaryService(),
        max_chunk_size=max_chunk_size,
    )


@pytest.mark.unit
class TestSplitByParagraphs:
    """Tests for SPLIT_BY_PARAGRAPHS strategy per BR-EMBEDDING-001."""

    @pytest.mark.asyncio
    async def test_two_paragraphs_produce_two_chunks(self):
        """Each paragraph (>= 20 words) produces an independent chunk."""
        text = f"{P_PEDIDO}\n\n{P_CICLO}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(text), _make_schema())

        assert len(chunks) == 2
        assert chunks[0].chunk_type == "paragraph"
        assert chunks[1].chunk_type == "paragraph"
        assert "pedido de compra" in chunks[0].content
        assert "ciclo de vida" in chunks[1].content

    @pytest.mark.asyncio
    async def test_short_paragraph_merged_with_next(self):
        """Paragraphs with < 20 words are merged with the next one."""
        short = "Párrafo corto introductorio."
        text = f"{short}\n\n{P_PEDIDO}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(text), _make_schema())

        assert len(chunks) == 1
        assert "Párrafo corto" in chunks[0].content
        assert "pedido de compra" in chunks[0].content

    @pytest.mark.asyncio
    async def test_multiple_short_paragraphs_merged_until_threshold(self):
        """Multiple short paragraphs accumulate until >= 20 words."""
        p1 = "Primera frase corta."
        p2 = "Segunda frase corta."
        p3 = "Tercera frase corta."
        text = f"{p1}\n\n{p2}\n\n{p3}\n\n{P_PEDIDO}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(text), _make_schema())

        assert len(chunks) == 1
        assert "Primera frase" in chunks[0].content
        assert "pedido de compra" in chunks[0].content

    @pytest.mark.asyncio
    async def test_trailing_short_paragraph_appended_to_last(self):
        """A trailing short paragraph is appended to the last chunk."""
        trailing = "Nota final breve."
        text = f"{P_PEDIDO}\n\n{trailing}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(text), _make_schema())

        assert len(chunks) == 1
        assert "Nota final breve." in chunks[0].content
        assert "pedido de compra" in chunks[0].content

    @pytest.mark.asyncio
    async def test_single_paragraph_produces_one_chunk(self):
        """A single paragraph produces exactly one chunk."""
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(P_PEDIDO), _make_schema())

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "paragraph"

    @pytest.mark.asyncio
    async def test_empty_content_produces_no_chunks(self):
        """Empty content produces zero chunks."""
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(""), _make_schema())

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_large_paragraph_falls_back_to_size_split(self):
        """A paragraph exceeding max_chunk_size is split by size."""
        large = " ".join(f"word{i}" for i in range(300))
        chunker = _make_chunker(max_chunk_size=200)
        chunks = await chunker.chunk(_make_parsed(large), _make_schema())

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.chunk_type == "text"

    @pytest.mark.asyncio
    async def test_chunk_ids_are_sequential(self):
        """Chunk IDs follow the doc_id#sequence pattern."""
        text = f"{P_PEDIDO}\n\n{P_CICLO}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(
            _make_parsed(text, doc_id="ENT-001"), _make_schema()
        )

        assert chunks[0].id == "ENT-001#0"
        assert chunks[1].id == "ENT-001#1"

    @pytest.mark.asyncio
    async def test_three_paragraphs_produce_three_chunks(self):
        """Three substantial paragraphs produce three chunks (BR-EMBEDDING-001 example)."""
        text = f"{P_PEDIDO}\n\n{P_CICLO}\n\n{P_LINEAS}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(text), _make_schema())

        assert len(chunks) == 3
        assert "pedido de compra" in chunks[0].content
        assert "ciclo de vida" in chunks[1].content
        assert "líneas con productos" in chunks[2].content

    @pytest.mark.asyncio
    async def test_contextualized_content_includes_prefix(self):
        """Each chunk's contextualized_content includes the hierarchical prefix."""
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(P_PEDIDO), _make_schema())

        assert len(chunks) == 1
        assert chunks[0].contextualized_content != chunks[0].content
        assert chunks[0].content in chunks[0].contextualized_content

    @pytest.mark.asyncio
    async def test_whitespace_only_paragraphs_ignored(self):
        """Blank lines between paragraphs don't produce empty chunks."""
        text = f"{P_PEDIDO}\n\n   \n\n{P_CICLO}"
        chunker = _make_chunker()
        chunks = await chunker.chunk(_make_parsed(text), _make_schema())

        assert len(chunks) == 2


@pytest.mark.unit
class TestEntitySchemaUsesParagraphSplitting:
    """Verify entity schema uses SPLIT_BY_PARAGRAPHS for Descripción."""

    def test_descripcion_strategy(self):
        from kb_engine.smart.schemas.entity import ENTITY_SCHEMA

        descripcion = next(
            s for s in ENTITY_SCHEMA.required_sections if s.name == "Descripción"
        )
        assert descripcion.chunking_strategy == ChunkingStrategy.SPLIT_BY_PARAGRAPHS
