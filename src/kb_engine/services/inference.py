"""Inference service."""

from kb_engine.core.models.search import RetrievalMode, SearchFilters, SearchResponse
from kb_engine.pipelines.inference import InferencePipeline


class InferenceService:
    """Service for inference/query operations."""

    def __init__(self, pipeline: InferencePipeline) -> None:
        self._pipeline = pipeline

    async def search(
        self,
        query: str,
        mode: RetrievalMode | str = RetrievalMode.HYBRID,
        filters: SearchFilters | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> SearchResponse:
        """Execute a search query."""
        # Convert string mode to enum if needed
        if isinstance(mode, str):
            mode = RetrievalMode(mode.lower())

        return await self._pipeline.search(
            query=query,
            mode=mode,
            filters=filters,
            limit=limit,
            score_threshold=score_threshold,
        )

    async def vector_search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 10,
    ) -> SearchResponse:
        """Execute a vector-only search."""
        return await self.search(
            query=query,
            mode=RetrievalMode.VECTOR,
            filters=filters,
            limit=limit,
        )

    async def graph_search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 10,
    ) -> SearchResponse:
        """Execute a graph-only search."""
        return await self.search(
            query=query,
            mode=RetrievalMode.GRAPH,
            filters=filters,
            limit=limit,
        )

    async def hybrid_search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 10,
    ) -> SearchResponse:
        """Execute a hybrid (vector + graph) search."""
        return await self.search(
            query=query,
            mode=RetrievalMode.HYBRID,
            filters=filters,
            limit=limit,
        )
