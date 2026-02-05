"""Repository factory for creating repository instances."""

from typing import TYPE_CHECKING

from kb_engine.core.interfaces.repositories import (
    GraphRepository,
    TraceabilityRepository,
    VectorRepository,
)

if TYPE_CHECKING:
    from kb_engine.config.settings import Settings


class RepositoryFactory:
    """Factory for creating repository instances.

    Creates the appropriate repository implementations based on
    configuration settings.
    """

    def __init__(self, settings: "Settings") -> None:
        self._settings = settings
        self._traceability: TraceabilityRepository | None = None
        self._vector: VectorRepository | None = None
        self._graph: GraphRepository | None = None

    async def get_traceability_repository(self) -> TraceabilityRepository:
        """Get or create the traceability repository (PostgreSQL)."""
        if self._traceability is None:
            from kb_engine.repositories.traceability.postgres import PostgresRepository

            self._traceability = PostgresRepository(
                connection_string=self._settings.database_url,
            )
        return self._traceability

    async def get_vector_repository(self) -> VectorRepository:
        """Get or create the vector repository."""
        if self._vector is None:
            vector_store = self._settings.vector_store.lower()

            if vector_store == "qdrant":
                from kb_engine.repositories.vector.qdrant import QdrantRepository

                self._vector = QdrantRepository(
                    host=self._settings.qdrant_host,
                    port=self._settings.qdrant_port,
                    api_key=self._settings.qdrant_api_key,
                    collection_name=self._settings.qdrant_collection,
                )
            elif vector_store == "pgvector":
                from kb_engine.repositories.vector.pgvector import PGVectorRepository

                self._vector = PGVectorRepository(
                    connection_string=self._settings.database_url,
                )
            elif vector_store == "weaviate":
                from kb_engine.repositories.vector.weaviate import WeaviateRepository

                self._vector = WeaviateRepository(
                    host=self._settings.weaviate_host,
                    api_key=self._settings.weaviate_api_key,
                )
            else:
                raise ValueError(f"Unknown vector store: {vector_store}")

        return self._vector

    async def get_graph_repository(self) -> GraphRepository:
        """Get or create the graph repository."""
        if self._graph is None:
            graph_store = self._settings.graph_store.lower()

            if graph_store == "neo4j":
                from kb_engine.repositories.graph.neo4j import Neo4jRepository

                self._graph = Neo4jRepository(
                    uri=self._settings.neo4j_uri,
                    user=self._settings.neo4j_user,
                    password=self._settings.neo4j_password,
                )
            elif graph_store == "nebula":
                from kb_engine.repositories.graph.nebula import NebulaRepository

                self._graph = NebulaRepository(
                    host=self._settings.nebula_host,
                    port=self._settings.nebula_port,
                )
            else:
                raise ValueError(f"Unknown graph store: {graph_store}")

        return self._graph

    async def close(self) -> None:
        """Close all repository connections."""
        # Implementations should handle their own cleanup
        self._traceability = None
        self._vector = None
        self._graph = None
