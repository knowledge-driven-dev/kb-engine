"""Hierarchical chunker with context-aware chunks."""

from uuid import uuid4

import structlog

from kb_engine.smart.chunking.summarizer import SummaryService
from kb_engine.smart.types import (
    ChunkingStrategy,
    ContentExpectation,
    ContextualizedChunk,
    HierarchicalContext,
    ParsedDocument,
    ParsedSection,
    ParsedTable,
    TemplateSchema,
)

logger = structlog.get_logger(__name__)


class HierarchicalChunker:
    """Generates contextualized chunks with hierarchical summaries."""

    def __init__(
        self,
        summary_service: SummaryService,
        max_chunk_size: int = 1024,
        chunk_overlap: int = 50,
    ) -> None:
        """Initialize the hierarchical chunker."""
        self.summary_service = summary_service
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    async def chunk(
        self,
        parsed: ParsedDocument,
        schema: TemplateSchema,
    ) -> list[ContextualizedChunk]:
        """Generate contextualized chunks from parsed document."""
        log = logger.bind(doc_title=parsed.title)
        log.debug("chunker.start", sections=len(parsed.sections))

        chunks: list[ContextualizedChunk] = []
        sequence = 0

        # Generate document summary
        log.debug("chunker.summarize_doc.start")
        doc_summary = await self.summary_service.summarize_document(parsed)
        log.debug("chunker.summarize_doc.complete", summary_length=len(doc_summary))

        doc_id = parsed.frontmatter.get("id", str(uuid4())[:8])

        for section in parsed.sections:
            section_log = log.bind(section=section.name)
            section_log.debug("chunker.section.start")

            section_summary = await self.summary_service.summarize_section(section, doc_summary)
            section_log.debug("chunker.section.summary", summary_length=len(section_summary))

            context = HierarchicalContext(
                document_summary=doc_summary,
                section_summaries=[section_summary],
                heading_path=[parsed.title, section.name],
            )

            strategy = self._get_strategy(section, schema)
            section_log.debug("chunker.section.strategy", strategy=strategy.value)

            if strategy == ChunkingStrategy.TABLE_ROWS and section.tables:
                for table in section.tables:
                    table_chunks = self._chunk_table_rows(
                        table=table,
                        context=context,
                        doc_id=doc_id,
                        doc_kind=parsed.kind,
                        section_name=section.name,
                        start_sequence=sequence,
                    )
                    chunks.extend(table_chunks)
                    sequence += len(table_chunks)
                    section_log.debug("chunker.section.table_rows", rows=len(table_chunks))

                non_table_text = self._extract_non_table_text(section)
                if non_table_text.strip():
                    text_chunks = self._chunk_text(
                        text=non_table_text,
                        context=context,
                        doc_id=doc_id,
                        doc_kind=parsed.kind,
                        section_name=section.name,
                        start_sequence=sequence,
                    )
                    chunks.extend(text_chunks)
                    sequence += len(text_chunks)

            elif strategy == ChunkingStrategy.KEEP_INTACT:
                chunk = self._create_chunk(
                    content=section.content,
                    context=context,
                    chunk_type="section",
                    doc_id=doc_id,
                    doc_kind=parsed.kind,
                    section_name=section.name,
                    sequence=sequence,
                    start_offset=section.start_offset,
                    end_offset=section.end_offset,
                )
                chunks.append(chunk)
                sequence += 1
                section_log.debug("chunker.section.keep_intact", content_length=len(section.content))

            elif strategy == ChunkingStrategy.SPLIT_BY_PARAGRAPHS:
                text_chunks = self._split_by_paragraphs(
                    text=section.content,
                    context=context,
                    doc_id=doc_id,
                    doc_kind=parsed.kind,
                    section_name=section.name,
                    start_sequence=sequence,
                )
                chunks.extend(text_chunks)
                sequence += len(text_chunks)
                section_log.debug("chunker.section.paragraphs", count=len(text_chunks))

            elif strategy == ChunkingStrategy.SPLIT_BY_ITEMS:
                items = self._extract_list_items(section.content)
                for item in items:
                    chunk = self._create_chunk(
                        content=item,
                        context=context,
                        chunk_type="list_item",
                        doc_id=doc_id,
                        doc_kind=parsed.kind,
                        section_name=section.name,
                        sequence=sequence,
                    )
                    chunks.append(chunk)
                    sequence += 1
                section_log.debug("chunker.section.list_items", count=len(items))

            else:  # DEFAULT
                text_chunks = self._chunk_text(
                    text=section.content,
                    context=context,
                    doc_id=doc_id,
                    doc_kind=parsed.kind,
                    section_name=section.name,
                    start_sequence=sequence,
                )
                chunks.extend(text_chunks)
                sequence += len(text_chunks)
                section_log.debug("chunker.section.text_chunks", count=len(text_chunks))

            section_log.debug("chunker.section.complete", total_chunks=sequence)

        log.debug("chunker.complete", total_chunks=len(chunks))
        return chunks

    def _get_strategy(self, section: ParsedSection, schema: TemplateSchema) -> ChunkingStrategy:
        """Determine chunking strategy for a section."""
        section_lower = section.name.lower()

        for sec_def in schema.required_sections + schema.optional_sections:
            names = [sec_def.name.lower()] + [a.lower() for a in sec_def.aliases]
            if section_lower in names:
                return sec_def.chunking_strategy

        if section.tables:
            return ChunkingStrategy.TABLE_ROWS

        if section.content_type in (
            ContentExpectation.MERMAID_STATE,
            ContentExpectation.MERMAID_FLOW,
            ContentExpectation.YAML,
            ContentExpectation.JSON,
        ):
            return ChunkingStrategy.KEEP_INTACT

        if len(section.content) <= self.max_chunk_size:
            return ChunkingStrategy.KEEP_INTACT

        return ChunkingStrategy.DEFAULT

    def _chunk_table_rows(
        self,
        table: ParsedTable,
        context: HierarchicalContext,
        doc_id: str,
        doc_kind,
        section_name: str,
        start_sequence: int,
    ) -> list[ContextualizedChunk]:
        """Generate one chunk per table row."""
        chunks: list[ContextualizedChunk] = []
        header_str = " | ".join(table.headers)

        for i, row in enumerate(table.rows):
            row_content = self._format_table_row(table.headers, row)

            row_context = HierarchicalContext(
                document_summary=context.document_summary,
                section_summaries=context.section_summaries + [f"Tabla: {header_str}"],
                heading_path=context.heading_path,
            )

            row_data = dict(zip(table.headers, row)) if len(row) == len(table.headers) else None

            chunk = self._create_chunk(
                content=row_content,
                context=row_context,
                chunk_type="table_row",
                doc_id=doc_id,
                doc_kind=doc_kind,
                section_name=section_name,
                sequence=start_sequence + i,
                table_headers=table.headers,
                row_index=i,
                row_data=row_data,
            )
            chunks.append(chunk)

        return chunks

    def _format_table_row(self, headers: list[str], row: list[str]) -> str:
        """Format a table row as readable text."""
        parts = []
        for i, header in enumerate(headers):
            value = row[i] if i < len(row) else ""
            if value.strip():
                parts.append(f"**{header}**: {value}")
        return "\n".join(parts)

    def _chunk_text(
        self,
        text: str,
        context: HierarchicalContext,
        doc_id: str,
        doc_kind,
        section_name: str,
        start_sequence: int,
    ) -> list[ContextualizedChunk]:
        """Split text into chunks with overlap."""
        chunks: list[ContextualizedChunk] = []

        if len(text) <= self.max_chunk_size:
            chunk = self._create_chunk(
                content=text,
                context=context,
                chunk_type="text",
                doc_id=doc_id,
                doc_kind=doc_kind,
                section_name=section_name,
                sequence=start_sequence,
            )
            return [chunk]

        current_pos = 0
        seq = start_sequence

        while current_pos < len(text):
            end_pos = min(current_pos + self.max_chunk_size, len(text))

            if end_pos < len(text):
                for sep in [". ", ".\n", "\n\n", "\n"]:
                    last_sep = text.rfind(sep, current_pos, end_pos)
                    if last_sep > current_pos:
                        end_pos = last_sep + len(sep)
                        break

            chunk_text = text[current_pos:end_pos].strip()
            if chunk_text:
                chunk = self._create_chunk(
                    content=chunk_text,
                    context=context,
                    chunk_type="text",
                    doc_id=doc_id,
                    doc_kind=doc_kind,
                    section_name=section_name,
                    sequence=seq,
                )
                chunks.append(chunk)
                seq += 1

            if end_pos >= len(text):
                break
            current_pos = end_pos - self.chunk_overlap

        return chunks

    MIN_PARAGRAPH_WORDS = 20

    def _split_by_paragraphs(
        self,
        text: str,
        context: HierarchicalContext,
        doc_id: str,
        doc_kind,
        section_name: str,
        start_sequence: int,
    ) -> list[ContextualizedChunk]:
        """Split text into chunks by paragraph per BR-EMBEDDING-001.

        Rules:
        1. Each paragraph (separated by blank lines) produces one chunk.
        2. Paragraphs with < 20 words are merged with the next paragraph.
        3. If a merged paragraph exceeds max_chunk_size, fall back to
           size-based splitting for that paragraph.
        """
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not raw_paragraphs:
            return []

        # Merge short paragraphs (< 20 words) with the next one
        merged: list[str] = []
        buffer = ""
        for para in raw_paragraphs:
            if buffer:
                buffer = f"{buffer}\n\n{para}"
            else:
                buffer = para

            if len(buffer.split()) >= self.MIN_PARAGRAPH_WORDS:
                merged.append(buffer)
                buffer = ""

        # Flush remaining buffer
        if buffer:
            if merged:
                merged[-1] = f"{merged[-1]}\n\n{buffer}"
            else:
                merged.append(buffer)

        # Create chunks, falling back to size-based splitting for large paragraphs
        chunks: list[ContextualizedChunk] = []
        seq = start_sequence
        for para in merged:
            if len(para) > self.max_chunk_size:
                sub_chunks = self._chunk_text(
                    text=para,
                    context=context,
                    doc_id=doc_id,
                    doc_kind=doc_kind,
                    section_name=section_name,
                    start_sequence=seq,
                )
                chunks.extend(sub_chunks)
                seq += len(sub_chunks)
            else:
                chunk = self._create_chunk(
                    content=para,
                    context=context,
                    chunk_type="paragraph",
                    doc_id=doc_id,
                    doc_kind=doc_kind,
                    section_name=section_name,
                    sequence=seq,
                )
                chunks.append(chunk)
                seq += 1

        return chunks

    def _extract_non_table_text(self, section: ParsedSection) -> str:
        """Extract text content that's not part of tables."""
        content = section.content
        for table in section.tables:
            content = content.replace(table.raw_content, "")
        return content.strip()

    def _extract_list_items(self, content: str) -> list[str]:
        """Extract list items from content."""
        import re
        items = re.findall(r"^[-*]\s+(.+)$", content, re.MULTILINE)
        return items if items else [content]

    def _create_chunk(
        self,
        content: str,
        context: HierarchicalContext,
        chunk_type: str,
        doc_id: str,
        doc_kind,
        section_name: str,
        sequence: int,
        start_offset: int | None = None,
        end_offset: int | None = None,
        table_headers: list[str] | None = None,
        row_index: int | None = None,
        row_data: dict[str, str] | None = None,
    ) -> ContextualizedChunk:
        """Create a contextualized chunk."""
        context_prefix = context.as_prefix()
        contextualized = f"{context_prefix}\n\n{content}" if context_prefix else content

        chunk_id = f"{doc_id}#{sequence}"

        return ContextualizedChunk(
            id=chunk_id,
            content=content,
            contextualized_content=contextualized,
            chunk_type=chunk_type,
            context=context,
            document_id=doc_id,
            document_kind=doc_kind,
            section_name=section_name,
            sequence=sequence,
            table_headers=table_headers,
            row_index=row_index,
            row_data=row_data,
            start_offset=start_offset,
            end_offset=end_offset,
        )
