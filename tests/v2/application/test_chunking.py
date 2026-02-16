"""Tests for kdd.application.chunking module."""

from kdd.application.chunking import Chunk, chunk_document
from kdd.domain.entities import KDDDocument, Section
from kdd.domain.enums import KDDKind, KDDLayer


def _make_document(
    kind: KDDKind,
    sections: list[Section],
    doc_id: str = "TEST-001",
) -> KDDDocument:
    return KDDDocument(
        id=doc_id,
        kind=kind,
        source_path="specs/01-domain/entities/Test.md",
        source_hash="abc123",
        layer=KDDLayer.DOMAIN,
        front_matter={"id": doc_id, "kind": kind.value, "status": "draft"},
        sections=sections,
    )


class TestChunkDocument:
    def test_event_produces_no_chunks(self):
        """Events have no embeddable sections per BR-EMBEDDING-001."""
        doc = _make_document(
            KDDKind.EVENT,
            [Section(heading="Descripción", level=2, content="Some event description.")],
        )
        chunks = chunk_document(doc)
        assert chunks == []

    def test_entity_embeds_description(self):
        doc = _make_document(
            KDDKind.ENTITY,
            [
                Section(heading="Descripción", level=2, content="An entity that represents orders."),
                Section(heading="Atributos", level=2, content="| name | type |\n|---|---|\n| id | UUID |"),
            ],
        )
        chunks = chunk_document(doc)
        assert len(chunks) >= 1
        # Only Descripción should be chunked, not Atributos
        assert all(c.section_heading == "Descripción" for c in chunks)

    def test_chunk_has_context_text(self):
        doc = _make_document(
            KDDKind.ENTITY,
            [Section(heading="Descripción", level=2, content="An entity representing orders.")],
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        # Context should include document identity
        assert "Document: TEST-001" in chunks[0].context_text
        assert "Kind: entity" in chunks[0].context_text
        assert "Section: Descripción" in chunks[0].context_text

    def test_chunk_id_format(self):
        doc = _make_document(
            KDDKind.ENTITY,
            [Section(heading="Descripción", level=2, content="Short description.")],
        )
        chunks = chunk_document(doc)
        assert chunks[0].chunk_id == "TEST-001:chunk-0"

    def test_multiple_embeddable_sections(self):
        """Business rules embed both Declaración and Cuándo Aplica."""
        doc = _make_document(
            KDDKind.BUSINESS_RULE,
            [
                Section(heading="Declaración", level=2, content="Rule declaration text."),
                Section(heading="Cuándo Aplica", level=2, content="When this rule applies."),
                Section(heading="Ejemplos", level=2, content="Example text not embedded."),
            ],
        )
        chunks = chunk_document(doc)
        headings = {c.section_heading for c in chunks}
        assert "Declaración" in headings
        assert "Cuándo Aplica" in headings
        assert "Ejemplos" not in headings

    def test_long_content_splits(self):
        """Content exceeding max_chunk_chars is split into multiple chunks."""
        long_text = "\n\n".join(f"Paragraph {i} with enough text." for i in range(50))
        doc = _make_document(
            KDDKind.ENTITY,
            [Section(heading="Descripción", level=2, content=long_text)],
        )
        chunks = chunk_document(doc, max_chunk_chars=200, overlap_chars=50)
        assert len(chunks) > 1

    def test_empty_section_skipped(self):
        doc = _make_document(
            KDDKind.ENTITY,
            [
                Section(heading="Descripción", level=2, content=""),
                Section(heading="Atributos", level=2, content="attr"),
            ],
        )
        chunks = chunk_document(doc)
        assert chunks == []

    def test_use_case_embeds_description_and_main_flow(self):
        doc = _make_document(
            KDDKind.USE_CASE,
            [
                Section(heading="Descripción", level=2, content="UC description."),
                Section(heading="Flujo Principal", level=2, content="Step 1, step 2."),
                Section(heading="Actores", level=2, content="Developer"),
            ],
        )
        chunks = chunk_document(doc)
        headings = {c.section_heading for c in chunks}
        assert "Descripción" in headings
        assert "Flujo Principal" in headings
        assert "Actores" not in headings

    def test_prd_embeds_problem(self):
        doc = _make_document(
            KDDKind.PRD,
            [
                Section(heading="Problema / Oportunidad", level=2, content="The problem statement."),
                Section(heading="Alcance", level=2, content="Scope details."),
            ],
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].section_heading == "Problema / Oportunidad"
