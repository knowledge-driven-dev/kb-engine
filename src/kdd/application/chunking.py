"""Hierarchical chunking for embedding generation (BR-EMBEDDING-001).

Selects embeddable sections per kind, splits them into paragraph-level
chunks, and enriches each chunk with context (document identity + ancestry).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kdd.domain.entities import KDDDocument, Section
from kdd.domain.enums import KDDKind
from kdd.domain.rules import embeddable_sections


@dataclass(frozen=True)
class Chunk:
    """A text chunk ready for embedding."""

    chunk_id: str
    document_id: str
    section_heading: str
    content: str
    context_text: str
    char_offset: int = 0


def chunk_document(
    document: KDDDocument,
    *,
    max_chunk_chars: int = 1500,
    overlap_chars: int = 200,
) -> list[Chunk]:
    """Chunk a document's embeddable sections into embedding-ready pieces.

    Steps:
    1. Identify embeddable sections via BR-EMBEDDING-001.
    2. For each section, split into paragraph chunks.
    3. Enrich each chunk with context (document identity + section heading).

    Returns an empty list if the kind has no embeddable sections (e.g. event).
    """
    allowed = embeddable_sections(document.kind)
    if not allowed:
        return []

    # Build document identity context
    identity = _build_identity(document)

    chunks: list[Chunk] = []
    chunk_idx = 0

    for section in document.sections:
        if section.heading.lower() not in allowed:
            continue
        if not section.content.strip():
            continue

        paragraphs = _split_paragraphs(section.content, max_chunk_chars, overlap_chars)

        for offset, text in paragraphs:
            context = f"{identity}\nSection: {section.heading}\n\n{text}"
            chunks.append(Chunk(
                chunk_id=f"{document.id}:chunk-{chunk_idx}",
                document_id=document.id,
                section_heading=section.heading,
                content=text,
                context_text=context,
                char_offset=offset,
            ))
            chunk_idx += 1

    return chunks


def _build_identity(document: KDDDocument) -> str:
    """Build a concise identity string for context enrichment."""
    parts = [
        f"Document: {document.id}",
        f"Kind: {document.kind.value}",
        f"Layer: {document.layer.value}",
    ]
    title = document.front_matter.get("title")
    if title:
        parts.append(f"Title: {title}")
    return "\n".join(parts)


def _split_paragraphs(
    content: str,
    max_chars: int,
    overlap: int,
) -> list[tuple[int, str]]:
    """Split content into paragraph-boundary chunks.

    Returns list of (char_offset, text) tuples.

    Strategy:
    - Split on double newlines (paragraph boundaries).
    - Accumulate paragraphs until max_chars is reached.
    - When a single paragraph exceeds max_chars, split at sentence
      boundaries within it.
    """
    paragraphs = content.split("\n\n")
    results: list[tuple[int, str]] = []

    current_parts: list[str] = []
    current_len = 0
    current_offset = 0
    char_pos = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            char_pos += 2  # account for \n\n
            continue

        para_len = len(para)

        if current_len + para_len + 2 > max_chars and current_parts:
            # Flush current accumulation
            results.append((current_offset, "\n\n".join(current_parts)))
            # Overlap: keep last part if it fits
            if overlap > 0 and current_parts:
                last = current_parts[-1]
                if len(last) <= overlap:
                    current_parts = [last]
                    current_len = len(last)
                    current_offset = char_pos - len(last) - 2
                else:
                    current_parts = []
                    current_len = 0
                    current_offset = char_pos
            else:
                current_parts = []
                current_len = 0
                current_offset = char_pos

        if para_len > max_chars and not current_parts:
            # Single paragraph too large — split at sentence boundaries
            sentences = _split_sentences(para)
            sent_buf: list[str] = []
            sent_len = 0
            sent_offset = char_pos

            for sent in sentences:
                if sent_len + len(sent) + 1 > max_chars and sent_buf:
                    results.append((sent_offset, " ".join(sent_buf)))
                    sent_buf = []
                    sent_len = 0
                    sent_offset = char_pos
                sent_buf.append(sent)
                sent_len += len(sent) + 1

            if sent_buf:
                current_parts = sent_buf
                current_len = sent_len
                current_offset = sent_offset
        else:
            if not current_parts:
                current_offset = char_pos
            current_parts.append(para)
            current_len += para_len + 2

        char_pos += para_len + 2

    if current_parts:
        results.append((current_offset, "\n\n".join(current_parts)))

    return results


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter: split on `. ` or `.\n`."""
    import re
    parts = re.split(r"(?<=\.)\s+", text)
    return [p.strip() for p in parts if p.strip()]
