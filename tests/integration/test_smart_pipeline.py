"""Integration tests for the smart pipeline with Kuzu."""

import asyncio
import shutil
from pathlib import Path

import pytest

from kb_engine.smart import (
    DocumentKindDetector,
    EntityIngestionPipeline,
    EntityParser,
    KDDDocumentKind,
    KuzuGraphStore,
)

# Test fixtures
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "entities" / "Usuario.md"
TEST_GRAPH_PATH = Path("/tmp/kb-engine-test-graph")


@pytest.fixture(autouse=True)
def cleanup_graph():
    """Clean up test graph before and after tests."""
    def _cleanup():
        if TEST_GRAPH_PATH.exists():
            if TEST_GRAPH_PATH.is_dir():
                shutil.rmtree(TEST_GRAPH_PATH)
            else:
                TEST_GRAPH_PATH.unlink()
    _cleanup()
    yield
    _cleanup()


class TestDocumentKindDetector:
    """Tests for document kind detection."""

    def test_detect_entity_from_frontmatter(self):
        """Should detect entity kind from frontmatter."""
        content = FIXTURE_PATH.read_text()
        detector = DocumentKindDetector()

        result = detector.detect(content, "Usuario.md")

        assert result.kind == KDDDocumentKind.ENTITY
        assert result.confidence == 1.0
        assert result.detected_from == "frontmatter"

    def test_detect_unknown_without_frontmatter(self):
        """Should return unknown when no frontmatter kind is present."""
        content = "# Some Entity\n\nDescription here."
        detector = DocumentKindDetector()

        result = detector.detect(content, "Product.md")

        assert result.kind == KDDDocumentKind.UNKNOWN


class TestEntityParser:
    """Tests for entity document parsing."""

    def test_parse_entity_document(self):
        """Should parse entity document structure."""
        content = FIXTURE_PATH.read_text()
        parser = EntityParser()

        parsed = parser.parse(content, "Usuario.md")

        assert parsed.kind == KDDDocumentKind.ENTITY
        assert parsed.title == "Usuario"
        assert parsed.entity_name == "Usuario"
        assert "User" in parsed.aliases
        assert parsed.code_class == "User"
        assert parsed.code_table == "users"

    def test_extract_entity_info(self):
        """Should extract entity info from parsed document."""
        content = FIXTURE_PATH.read_text()
        parser = EntityParser()

        parsed = parser.parse(content, "Usuario.md")
        entity_info = parser.extract_entity_info(parsed)

        # Check attributes
        assert len(entity_info.attributes) >= 8
        attr_names = [a.name for a in entity_info.attributes]
        assert "id" in attr_names
        assert "email" in attr_names

        # Check relations
        assert len(entity_info.relations) >= 4

        # Check states
        assert len(entity_info.states) >= 5

        # Check events
        assert len(entity_info.events_emitted) >= 5


class TestKuzuGraphStore:
    """Tests for Kuzu graph store."""

    def test_initialize_and_upsert(self):
        """Should initialize store and upsert entities."""
        store = KuzuGraphStore(TEST_GRAPH_PATH)
        store.initialize()

        # Upsert entity
        store.upsert_entity(
            entity_id="entity:Test",
            name="Test",
            description="Test entity",
            code_class="Test",
        )

        # Query
        results = store.execute_cypher(
            "MATCH (e:Entity {name: 'Test'}) RETURN e.name as name"
        )

        assert len(results) == 1
        assert results[0]["name"] == "Test"

        store.close()

    def test_relationships(self):
        """Should create and query relationships."""
        store = KuzuGraphStore(TEST_GRAPH_PATH)
        store.initialize()

        # Create entities
        store.upsert_entity("entity:A", "EntityA", "First entity")
        store.upsert_concept("concept:A.attr", "attr", "attribute", "An attribute", "EntityA")

        # Create relationship
        store.add_contains("entity:A", "concept:A.attr")

        # Query relationship
        results = store.execute_cypher("""
            MATCH (e:Entity)-[:CONTAINS]->(c:Concept)
            RETURN e.name as entity, c.name as concept
        """)

        assert len(results) == 1
        assert results[0]["entity"] == "EntityA"
        assert results[0]["concept"] == "attr"

        store.close()


class TestEntityIngestionPipeline:
    """Integration tests for the full pipeline."""

    @pytest.mark.asyncio
    async def test_ingest_entity_document_skip_graph(self):
        """Should ingest entity document without storing to graph."""
        content = FIXTURE_PATH.read_text()

        pipeline = EntityIngestionPipeline(
            graph_path=TEST_GRAPH_PATH,
            use_mock_summarizer=True,
        )

        result = await pipeline.ingest(content, filename="Usuario.md", skip_graph=True)

        assert result.success
        assert result.document_kind == KDDDocumentKind.ENTITY
        assert result.document_id == "Usuario"
        assert result.chunks_created > 0
        assert result.entities_extracted > 0
        assert result.relations_created > 0
        assert len(result.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_ingest_entity_document_with_graph(self):
        """Should ingest entity document and store to Kuzu graph."""
        content = FIXTURE_PATH.read_text()

        pipeline = EntityIngestionPipeline(
            graph_path=TEST_GRAPH_PATH,
            use_mock_summarizer=True,
        )

        result = await pipeline.ingest(content, filename="Usuario.md", skip_graph=False)

        assert result.success
        assert result.entities_extracted > 0
        assert result.relations_created > 0

        # Verify data in graph
        stats = pipeline.get_graph_stats()
        assert stats["entity_count"] > 0

        # Query the graph
        entities = pipeline.query_graph(
            "MATCH (e:Entity {name: 'Usuario'}) RETURN e.name as name"
        )
        assert len(entities) == 1
        assert entities[0]["name"] == "Usuario"

        # Query relationships (CONTAINS)
        relations = pipeline.query_graph("""
            MATCH (e:Entity {name: 'Usuario'})-[:CONTAINS]->(c:Concept)
            RETURN c.name as concept, c.concept_type as ctype
        """)
        assert len(relations) > 0

        pipeline.close()

    @pytest.mark.asyncio
    async def test_reject_non_entity_document(self):
        """Should reject non-entity documents."""
        content = """---
kind: use-case
---

# Login de Usuario

## Resumen

El usuario inicia sesión.
"""
        pipeline = EntityIngestionPipeline(
            graph_path=TEST_GRAPH_PATH,
            use_mock_summarizer=True,
        )

        result = await pipeline.ingest(content, filename="UC-Login.md", skip_graph=True)

        assert not result.success
        assert "Expected entity document" in result.validation_errors[0]


# Quick manual test
async def main():
    """Run a quick test of the pipeline."""
    print("=" * 60)
    print("Testing Smart Pipeline with Kuzu")
    print("=" * 60)

    # Clean up
    if TEST_GRAPH_PATH.exists():
        shutil.rmtree(TEST_GRAPH_PATH)

    content = FIXTURE_PATH.read_text()
    print(f"\nLoaded: {FIXTURE_PATH.name} ({len(content)} chars)")

    # Create pipeline
    pipeline = EntityIngestionPipeline(
        graph_path=TEST_GRAPH_PATH,
        use_mock_summarizer=True,
    )

    # Ingest with graph storage
    print("\nIngesting document...")
    result = await pipeline.ingest(content, filename="Usuario.md", skip_graph=False)

    print(f"\nResult:")
    print(f"  - Success: {result.success}")
    print(f"  - Document ID: {result.document_id}")
    print(f"  - Chunks created: {result.chunks_created}")
    print(f"  - Entities extracted: {result.entities_extracted}")
    print(f"  - Relations created: {result.relations_created}")
    print(f"  - Processing time: {result.processing_time_ms:.2f}ms")

    # Query graph
    print("\n" + "-" * 60)
    print("Querying Kuzu Graph")
    print("-" * 60)

    print("\nEntities:")
    entities = pipeline.query_graph("MATCH (e:Entity) RETURN e.name as name, e.code_class as code")
    for e in entities:
        print(f"  - {e['name']} ({e['code']})")

    print("\nRelationships from Usuario:")
    # Query each relationship type separately (Kuzu doesn't have type() function)
    for rel_type in ["CONTAINS", "REFERENCES", "PRODUCES", "CONSUMES"]:
        rels = pipeline.query_graph(f"""
            MATCH (e:Entity {{name: 'Usuario'}})-[r:{rel_type}]->(n)
            RETURN label(n) as target_type, n.name as target_name
            LIMIT 5
        """)
        for r in rels:
            print(f"  - {rel_type} -> {r['target_type']}:{r['target_name']}")

    print("\nGraph stats:")
    stats = pipeline.get_graph_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    pipeline.close()

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
