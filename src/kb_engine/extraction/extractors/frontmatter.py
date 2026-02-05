"""Frontmatter-based entity extractor."""

from kb_engine.core.interfaces.extractors import ExtractionResult
from kb_engine.core.models.document import Chunk, Document
from kb_engine.core.models.graph import EdgeType, NodeType
from kb_engine.extraction.extractors.base import BaseExtractor
from kb_engine.extraction.models import ExtractedEdge, ExtractedNode


class FrontmatterExtractor(BaseExtractor):
    """Extracts entities from document frontmatter.

    KDD documents often have YAML frontmatter with structured
    metadata including tags, categories, and related entities.
    """

    @property
    def name(self) -> str:
        return "frontmatter"

    @property
    def priority(self) -> int:
        return 10  # High priority (runs first)

    def can_extract(self, chunk: Chunk, document: Document) -> bool:
        """Can extract if document has metadata."""
        return bool(document.metadata)

    async def extract(
        self,
        chunk: Chunk,
        document: Document,
    ) -> ExtractionResult:
        """Extract entities from document frontmatter."""
        nodes: list[ExtractedNode] = []
        edges: list[ExtractedEdge] = []

        metadata = document.metadata

        # Extract from tags
        if "tags" in metadata and isinstance(metadata["tags"], list):
            for tag in metadata["tags"]:
                nodes.append(
                    ExtractedNode(
                        name=str(tag),
                        node_type=NodeType.CONCEPT,
                        description=f"Tag: {tag}",
                        confidence=1.0,
                        extraction_method=self.name,
                    )
                )

        # Extract from domain
        if document.domain:
            nodes.append(
                ExtractedNode(
                    name=document.domain,
                    node_type=NodeType.CONCEPT,
                    description=f"Domain: {document.domain}",
                    confidence=1.0,
                    extraction_method=self.name,
                )
            )

        # Create document node
        doc_node = ExtractedNode(
            name=document.title,
            node_type=NodeType.DOCUMENT,
            description=f"Document: {document.title}",
            properties={"source_path": document.source_path},
            confidence=1.0,
            extraction_method=self.name,
        )
        nodes.append(doc_node)

        # Create edges from document to tags/domain
        for node in nodes:
            if node.node_type == NodeType.CONCEPT:
                edges.append(
                    ExtractedEdge(
                        source_name=document.title,
                        target_name=node.name,
                        edge_type=EdgeType.RELATED_TO,
                        confidence=1.0,
                        extraction_method=self.name,
                    )
                )

        # Extract related documents
        if "related" in metadata and isinstance(metadata["related"], list):
            for related in metadata["related"]:
                edges.append(
                    ExtractedEdge(
                        source_name=document.title,
                        target_name=str(related),
                        edge_type=EdgeType.REFERENCES,
                        confidence=0.9,
                        extraction_method=self.name,
                    )
                )

        return ExtractionResult(nodes=nodes, edges=edges)  # type: ignore
