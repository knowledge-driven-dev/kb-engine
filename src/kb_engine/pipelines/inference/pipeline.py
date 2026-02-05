"""Main inference pipeline."""

import time

from kb_engine.core.interfaces.repositories import (
    GraphRepository,
    TraceabilityRepository,
    VectorRepository,
)
from kb_engine.core.models.search import (
    RetrievalMode,
    SearchFilters,
    SearchResponse,
    SearchResult,
)
from kb_engine.embedding import EmbeddingConfig, EmbeddingProviderFactory


class InferencePipeline:
    """Pipeline for processing inference queries.

    Orchestrates the retrieval process:
    1. Embed the query
    2. Retrieve relevant chunks (vector, graph, or hybrid)
    3. Rerank results
    4. Return structured response
    """

    def __init__(
        self,
        traceability_repo: TraceabilityRepository,
        vector_repo: VectorRepository,
        graph_repo: GraphRepository,
        embedding_config: EmbeddingConfig | None = None,
    ) -> None:
        self._traceability = traceability_repo
        self._vector = vector_repo
        self._graph = graph_repo

        # Initialize embedding provider
        self._embedding_provider = EmbeddingProviderFactory(embedding_config).create_provider()

    async def search(
        self,
        query: str,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        filters: SearchFilters | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> SearchResponse:
        """Execute a search query.

        Args:
            query: The search query text.
            mode: Retrieval mode (vector, graph, or hybrid).
            filters: Optional filters to apply.
            limit: Maximum number of results.
            score_threshold: Minimum score threshold.

        Returns:
            SearchResponse with ranked results.
        """
        start_time = time.time()

        results: list[SearchResult] = []

        if mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
            vector_results = await self._vector_search(
                query, filters, limit, score_threshold
            )
            results.extend(vector_results)

        if mode in (RetrievalMode.GRAPH, RetrievalMode.HYBRID):
            graph_results = await self._graph_search(query, filters, limit)
            results.extend(graph_results)

        # Deduplicate and merge results if hybrid
        if mode == RetrievalMode.HYBRID:
            results = self._merge_results(results, limit)

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:limit]

        processing_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=results,
            total_count=len(results),
            retrieval_mode=mode,
            filters_applied=filters,
            processing_time_ms=processing_time,
        )

    async def _vector_search(
        self,
        query: str,
        filters: SearchFilters | None,
        limit: int,
        score_threshold: float | None,
    ) -> list[SearchResult]:
        """Perform vector similarity search."""
        # Embed the query
        query_vector = await self._embedding_provider.embed_text(query)

        # Search vector store
        chunk_scores = await self._vector.search(
            query_vector=query_vector,
            limit=limit,
            filters=filters,
            score_threshold=score_threshold,
        )

        # Fetch chunk details
        results = []
        for chunk_id, score in chunk_scores:
            chunk = await self._traceability.get_chunk(chunk_id)
            if chunk:
                results.append(
                    SearchResult(
                        chunk=chunk,
                        score=score,
                        retrieval_mode=RetrievalMode.VECTOR,
                    )
                )

        return results

    async def _graph_search(
        self,
        query: str,
        filters: SearchFilters | None,
        limit: int,
    ) -> list[SearchResult]:
        """Perform graph-based search.

        TODO: Implement graph traversal search strategy.
        """
        # Placeholder - would implement graph traversal
        return []

    def _merge_results(
        self,
        results: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """Merge and deduplicate results from multiple sources.

        Uses Reciprocal Rank Fusion (RRF) for combining scores.
        """
        chunk_scores: dict[str, tuple[SearchResult, float]] = {}
        k = 60  # RRF constant

        for rank, result in enumerate(results):
            chunk_id = str(result.chunk.id)
            rrf_score = 1.0 / (k + rank + 1)

            if chunk_id in chunk_scores:
                existing_result, existing_score = chunk_scores[chunk_id]
                # Combine scores and merge graph context
                existing_result.graph_context.extend(result.graph_context)
                chunk_scores[chunk_id] = (existing_result, existing_score + rrf_score)
            else:
                chunk_scores[chunk_id] = (result, rrf_score)

        # Update scores and sort
        merged_results = []
        for result, rrf_score in chunk_scores.values():
            result.score = rrf_score
            result.retrieval_mode = RetrievalMode.HYBRID
            merged_results.append(result)

        merged_results.sort(key=lambda r: r.score, reverse=True)
        return merged_results[:limit]
