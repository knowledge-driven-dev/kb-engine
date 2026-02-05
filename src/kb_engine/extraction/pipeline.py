"""Extraction pipeline for orchestrating multiple extractors."""

from kb_engine.core.interfaces.extractors import EntityExtractor, ExtractionResult
from kb_engine.core.models.document import Chunk, Document
from kb_engine.extraction.config import ExtractionConfig
from kb_engine.extraction.models import ExtractedEdge, ExtractedNode


class ExtractionPipeline:
    """Pipeline for running multiple extractors on chunks.

    Orchestrates extraction by running all registered extractors
    in priority order, then deduplicating and merging results.
    """

    def __init__(
        self,
        config: ExtractionConfig | None = None,
        extractors: list[EntityExtractor] | None = None,
    ) -> None:
        self._config = config or ExtractionConfig()
        self._extractors: list[EntityExtractor] = extractors or []

    def register_extractor(self, extractor: EntityExtractor) -> None:
        """Register an extractor to the pipeline."""
        self._extractors.append(extractor)
        # Sort by priority (lower = higher priority)
        self._extractors.sort(key=lambda e: e.priority)

    async def extract(
        self,
        chunk: Chunk,
        document: Document,
    ) -> ExtractionResult:
        """Run all applicable extractors on a chunk.

        Returns combined and deduplicated extraction results.
        """
        all_nodes: list[ExtractedNode] = []
        all_edges: list[ExtractedEdge] = []

        for extractor in self._extractors:
            if extractor.can_extract(chunk, document):
                result = await extractor.extract(chunk, document)
                all_nodes.extend(result.nodes)
                all_edges.extend(result.edges)

        # Filter by confidence threshold
        filtered_nodes = [
            n for n in all_nodes if n.confidence >= self._config.confidence_threshold
        ]
        filtered_edges = [
            e for e in all_edges if e.confidence >= self._config.confidence_threshold
        ]

        # Deduplicate if enabled
        if self._config.deduplicate_entities:
            filtered_nodes = self._deduplicate_nodes(filtered_nodes)
            filtered_edges = self._deduplicate_edges(filtered_edges)

        return ExtractionResult(
            nodes=filtered_nodes,  # type: ignore
            edges=filtered_edges,  # type: ignore
        )

    async def extract_document(
        self,
        document: Document,
        chunks: list[Chunk],
    ) -> ExtractionResult:
        """Extract entities from all chunks of a document."""
        all_nodes: list[ExtractedNode] = []
        all_edges: list[ExtractedEdge] = []

        for chunk in chunks:
            result = await self.extract(chunk, document)
            all_nodes.extend(result.nodes)  # type: ignore
            all_edges.extend(result.edges)  # type: ignore

        # Final deduplication across all chunks
        if self._config.deduplicate_entities:
            all_nodes = self._deduplicate_nodes(all_nodes)
            all_edges = self._deduplicate_edges(all_edges)

        return ExtractionResult(
            nodes=all_nodes,  # type: ignore
            edges=all_edges,  # type: ignore
        )

    def _deduplicate_nodes(
        self,
        nodes: list[ExtractedNode],
    ) -> list[ExtractedNode]:
        """Deduplicate nodes by name and type.

        When duplicates are found, keeps the one with highest confidence.
        """
        seen: dict[tuple[str, str], ExtractedNode] = {}

        for node in nodes:
            key = (node.name.lower(), node.node_type.value)
            if key not in seen or node.confidence > seen[key].confidence:
                seen[key] = node

        return list(seen.values())

    def _deduplicate_edges(
        self,
        edges: list[ExtractedEdge],
    ) -> list[ExtractedEdge]:
        """Deduplicate edges by source, target, and type.

        When duplicates are found, keeps the one with highest confidence.
        """
        seen: dict[tuple[str, str, str], ExtractedEdge] = {}

        for edge in edges:
            key = (edge.source_name.lower(), edge.target_name.lower(), edge.edge_type.value)
            if key not in seen or edge.confidence > seen[key].confidence:
                seen[key] = edge

        return list(seen.values())
