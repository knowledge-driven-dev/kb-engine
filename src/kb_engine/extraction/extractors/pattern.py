"""Pattern-based entity extractor."""

import re
from typing import Any

from kb_engine.core.interfaces.extractors import ExtractionResult
from kb_engine.core.models.document import Chunk, ChunkType, Document
from kb_engine.core.models.graph import EdgeType, NodeType
from kb_engine.extraction.extractors.base import BaseExtractor
from kb_engine.extraction.models import ExtractedEdge, ExtractedNode


class PatternExtractor(BaseExtractor):
    """Extracts entities using regex patterns.

    Uses predefined patterns to identify entities, actors,
    and relationships from text.
    """

    # Patterns for different entity types
    ENTITY_PATTERNS: list[tuple[str, NodeType, float]] = [
        # Actor patterns
        (r"(?:actor|usuario|user|cliente|customer|administrador|admin)[\s:]+(\w+(?:\s+\w+)?)", NodeType.ACTOR, 0.8),
        # System patterns
        (r"(?:sistema|system|servicio|service|módulo|module)[\s:]+(\w+(?:\s+\w+)?)", NodeType.SYSTEM, 0.8),
        # Entity patterns
        (r"(?:entidad|entity|objeto|object)[\s:]+(\w+(?:\s+\w+)?)", NodeType.ENTITY, 0.8),
        # Use case patterns
        (r"(?:caso de uso|use case|CU[-_]?\d+)[\s:]+(\w+(?:\s+\w+)*)", NodeType.USE_CASE, 0.85),
        # Rule patterns
        (r"(?:regla|rule|RN[-_]?\d+|BR[-_]?\d+)[\s:]+(\w+(?:\s+\w+)*)", NodeType.RULE, 0.85),
    ]

    # Patterns for relationships
    RELATIONSHIP_PATTERNS: list[tuple[str, EdgeType, float]] = [
        # Dependency patterns
        (r"(\w+(?:\s+\w+)?)\s+(?:depende de|depends on)\s+(\w+(?:\s+\w+)?)", EdgeType.DEPENDS_ON, 0.75),
        # Usage patterns
        (r"(\w+(?:\s+\w+)?)\s+(?:usa|uses|utiliza|utilizes)\s+(\w+(?:\s+\w+)?)", EdgeType.USES, 0.75),
        # Production patterns
        (r"(\w+(?:\s+\w+)?)\s+(?:produce|produces|genera|generates)\s+(\w+(?:\s+\w+)?)", EdgeType.PRODUCES, 0.75),
        # Reference patterns
        (r"(\w+(?:\s+\w+)?)\s+(?:referencia|references|ver|see)\s+(\w+(?:\s+\w+)?)", EdgeType.REFERENCES, 0.7),
        # Implementation patterns
        (r"(\w+(?:\s+\w+)?)\s+(?:implementa|implements)\s+(\w+(?:\s+\w+)?)", EdgeType.IMPLEMENTS, 0.8),
    ]

    @property
    def name(self) -> str:
        return "pattern"

    @property
    def priority(self) -> int:
        return 20  # Medium priority

    def can_extract(self, chunk: Chunk, document: Document) -> bool:
        """Can extract from any chunk with content."""
        return bool(chunk.content and len(chunk.content) > 10)

    async def extract(
        self,
        chunk: Chunk,
        document: Document,
    ) -> ExtractionResult:
        """Extract entities using pattern matching."""
        nodes: list[ExtractedNode] = []
        edges: list[ExtractedEdge] = []

        content = chunk.content

        # Extract entities
        for pattern, node_type, base_confidence in self.ENTITY_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                if name and len(name) > 2:
                    # Adjust confidence based on chunk type alignment
                    confidence = self._adjust_confidence(
                        base_confidence, node_type, chunk.chunk_type
                    )
                    nodes.append(
                        ExtractedNode(
                            name=name,
                            node_type=node_type,
                            confidence=confidence,
                            extraction_method=self.name,
                            source_text=match.group(0),
                        )
                    )

        # Extract relationships
        for pattern, edge_type, confidence in self.RELATIONSHIP_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                source = match.group(1).strip()
                target = match.group(2).strip()
                if source and target and len(source) > 2 and len(target) > 2:
                    edges.append(
                        ExtractedEdge(
                            source_name=source,
                            target_name=target,
                            edge_type=edge_type,
                            confidence=confidence,
                            extraction_method=self.name,
                            source_text=match.group(0),
                        )
                    )

        return ExtractionResult(nodes=nodes, edges=edges)  # type: ignore

    def _adjust_confidence(
        self,
        base_confidence: float,
        node_type: NodeType,
        chunk_type: ChunkType,
    ) -> float:
        """Adjust confidence based on alignment between node and chunk types."""
        # Mapping of chunk types to expected node types
        type_alignment: dict[ChunkType, set[NodeType]] = {
            ChunkType.ENTITY: {NodeType.ENTITY, NodeType.CONCEPT},
            ChunkType.USE_CASE: {NodeType.USE_CASE, NodeType.ACTOR},
            ChunkType.RULE: {NodeType.RULE},
            ChunkType.PROCESS: {NodeType.PROCESS, NodeType.ACTOR, NodeType.SYSTEM},
        }

        expected_types = type_alignment.get(chunk_type, set())
        if node_type in expected_types:
            return min(1.0, base_confidence + 0.1)  # Boost confidence

        return base_confidence
