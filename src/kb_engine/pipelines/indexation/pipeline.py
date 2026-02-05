"""Main indexation pipeline."""

from datetime import datetime

from kb_engine.chunking import ChunkerFactory, ChunkingConfig
from kb_engine.core.exceptions import PipelineError
from kb_engine.core.interfaces.repositories import (
    GraphRepository,
    TraceabilityRepository,
    VectorRepository,
)
from kb_engine.core.models.document import Document, DocumentStatus
from kb_engine.core.models.graph import Node
from kb_engine.embedding import EmbeddingConfig, EmbeddingProviderFactory
from kb_engine.extraction import ExtractionConfig, ExtractionPipelineFactory
from kb_engine.utils.hashing import compute_content_hash


class IndexationPipeline:
    """Pipeline for indexing documents into the knowledge base.

    Orchestrates the full indexation process:
    1. Parse and validate document
    2. Chunk content using semantic strategies
    3. Generate embeddings
    4. Extract entities and relationships
    5. Store in all repositories
    """

    def __init__(
        self,
        traceability_repo: TraceabilityRepository,
        vector_repo: VectorRepository,
        graph_repo: GraphRepository,
        chunking_config: ChunkingConfig | None = None,
        embedding_config: EmbeddingConfig | None = None,
        extraction_config: ExtractionConfig | None = None,
    ) -> None:
        self._traceability = traceability_repo
        self._vector = vector_repo
        self._graph = graph_repo

        # Initialize components
        self._chunker = ChunkerFactory(chunking_config)
        self._embedding_provider = EmbeddingProviderFactory(embedding_config).create_provider()
        self._extraction_pipeline = ExtractionPipelineFactory(extraction_config).create_pipeline()

    async def index_document(self, document: Document) -> Document:
        """Index a document through the full pipeline.

        Args:
            document: The document to index.

        Returns:
            The indexed document with updated status.

        Raises:
            PipelineError: If any step of the pipeline fails.
        """
        try:
            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            document.content_hash = compute_content_hash(document.content)

            # 1. Save document to traceability store
            document = await self._traceability.save_document(document)

            # 2. Chunk the document
            chunks = self._chunker.chunk_document(document)

            # 3. Save chunks to traceability store
            chunks = await self._traceability.save_chunks(chunks)

            # 4. Generate embeddings
            embeddings = await self._embedding_provider.embed_chunks(chunks)

            # 5. Store embeddings in vector store
            await self._vector.upsert_embeddings(embeddings)

            # 6. Extract entities and relationships
            extraction_result = await self._extraction_pipeline.extract_document(
                document, chunks
            )

            # 7. Store in graph
            for node_data in extraction_result.nodes:
                node = Node(
                    name=node_data.name,
                    node_type=node_data.node_type,
                    description=node_data.description,
                    source_document_id=document.id,
                    properties=node_data.properties,
                    confidence=node_data.confidence,
                    extraction_method=node_data.extraction_method,
                )
                await self._graph.create_node(node)

            # 8. Update document status
            document.status = DocumentStatus.INDEXED
            document.indexed_at = datetime.utcnow()
            document = await self._traceability.update_document(document)

            return document

        except Exception as e:
            document.status = DocumentStatus.FAILED
            try:
                await self._traceability.update_document(document)
            except Exception:
                pass
            raise PipelineError(
                f"Failed to index document: {e}",
                details={"document_id": str(document.id)},
            ) from e

    async def reindex_document(self, document: Document) -> Document:
        """Reindex an existing document.

        Removes existing indexed data and re-runs the pipeline.
        """
        # Delete existing data
        await self._vector.delete_by_document(document.id)
        await self._graph.delete_by_document(document.id)
        await self._traceability.delete_chunks_by_document(document.id)

        # Reindex
        return await self.index_document(document)

    async def delete_document(self, document: Document) -> bool:
        """Delete a document and all its indexed data."""
        # Delete from all stores
        await self._vector.delete_by_document(document.id)
        await self._graph.delete_by_document(document.id)
        await self._traceability.delete_chunks_by_document(document.id)
        return await self._traceability.delete_document(document.id)
