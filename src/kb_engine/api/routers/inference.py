"""Inference API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from kb_engine.api.dependencies import InferenceServiceDep
from kb_engine.core.models.search import RetrievalMode, SearchFilters, SearchResponse

router = APIRouter(prefix="/inference")


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    mode: RetrievalMode = Field(
        default=RetrievalMode.HYBRID, description="Retrieval mode"
    )
    limit: int = Field(default=10, ge=1, le=100, description="Max results")
    score_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Min score threshold"
    )
    filters: SearchFilters | None = Field(default=None, description="Search filters")


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: InferenceServiceDep,
) -> SearchResponse:
    """Execute a search query against the knowledge base."""
    return await service.search(
        query=request.query,
        mode=request.mode,
        filters=request.filters,
        limit=request.limit,
        score_threshold=request.score_threshold,
    )


@router.get("/search", response_model=SearchResponse)
async def search_get(
    service: InferenceServiceDep,
    query: Annotated[str, Query(min_length=1, max_length=1000)],
    mode: RetrievalMode = RetrievalMode.HYBRID,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SearchResponse:
    """Execute a search query (GET variant for simple queries)."""
    return await service.search(
        query=query,
        mode=mode,
        limit=limit,
    )
