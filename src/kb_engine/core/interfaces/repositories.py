"""Repository protocols as defined in ADR-0001."""

from typing import Protocol
from uuid import UUID

from kb_engine.core.models.document import Chunk, Document
from kb_engine.core.models.embedding import Embedding
from kb_engine.core.models.graph import Edge, Node
from kb_engine.core.models.search import SearchFilters


class TraceabilityRepository(Protocol):
    """Protocol for the traceability store (PostgreSQL).

    Stores documents, chunks, and their relationships for
    full traceability and audit capabilities.
    """

    async def save_document(self, document: Document) -> Document:
        """Save a document to the store."""
        ...

    async def get_document(self, document_id: UUID) -> Document | None:
        """Get a document by ID."""
        ...

    async def get_document_by_external_id(self, external_id: str) -> Document | None:
        """Get a document by external ID."""
        ...

    async def list_documents(
        self,
        filters: SearchFilters | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """List documents with optional filters."""
        ...

    async def update_document(self, document: Document) -> Document:
        """Update an existing document."""
        ...

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete a document and its chunks."""
        ...

    async def save_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Save multiple chunks."""
        ...

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        """Get all chunks for a document."""
        ...

    async def get_chunk(self, chunk_id: UUID) -> Chunk | None:
        """Get a chunk by ID."""
        ...

    async def delete_chunks_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        ...


class VectorRepository(Protocol):
    """Protocol for the vector store (Qdrant/Weaviate/PGVector).

    Stores embeddings and provides similarity search.
    """

    async def upsert_embeddings(self, embeddings: list[Embedding]) -> int:
        """Upsert embeddings. Returns count upserted."""
        ...

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filters: SearchFilters | None = None,
        score_threshold: float | None = None,
    ) -> list[tuple[UUID, float]]:
        """Search for similar vectors. Returns (chunk_id, score) pairs."""
        ...

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all embeddings for a document. Returns count deleted."""
        ...

    async def delete_by_chunk_ids(self, chunk_ids: list[UUID]) -> int:
        """Delete embeddings by chunk IDs. Returns count deleted."""
        ...

    async def get_collection_info(self) -> dict[str, int | str]:
        """Get information about the collection."""
        ...


class GraphRepository(Protocol):
    """Protocol for the graph store (Neo4j/Nebula).

    Stores the knowledge graph for entity relationships.
    """

    async def create_node(self, node: Node) -> Node:
        """Create a node in the graph."""
        ...

    async def get_node(self, node_id: UUID) -> Node | None:
        """Get a node by ID."""
        ...

    async def find_nodes(
        self,
        node_type: str | None = None,
        name_pattern: str | None = None,
        limit: int = 100,
    ) -> list[Node]:
        """Find nodes by type or name pattern."""
        ...

    async def create_edge(self, edge: Edge) -> Edge:
        """Create an edge between nodes."""
        ...

    async def get_edges(
        self,
        node_id: UUID,
        direction: str = "both",  # "in", "out", "both"
        edge_type: str | None = None,
    ) -> list[Edge]:
        """Get edges connected to a node."""
        ...

    async def traverse(
        self,
        start_node_id: UUID,
        max_hops: int = 2,
        edge_types: list[str] | None = None,
    ) -> list[tuple[Node, Edge, Node]]:
        """Traverse the graph from a starting node. Returns (source, edge, target) triples."""
        ...

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all nodes and edges from a document. Returns count deleted."""
        ...

    async def find_similar_nodes(
        self,
        node_id: UUID,
        limit: int = 10,
    ) -> list[tuple[Node, float]]:
        """Find similar nodes based on graph structure. Returns (node, similarity) pairs."""
        ...
