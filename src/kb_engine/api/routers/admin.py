"""Admin API endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/admin")


class SystemStats(BaseModel):
    """System statistics."""

    documents_count: int
    chunks_count: int
    embeddings_count: int
    nodes_count: int
    edges_count: int


class StoreInfo(BaseModel):
    """Information about a data store."""

    name: str
    status: str
    details: dict


@router.get("/stats", response_model=SystemStats)
async def get_system_stats() -> dict:
    """Get system statistics.

    TODO: Implement with repositories.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin endpoints not yet implemented",
    )


@router.get("/stores", response_model=list[StoreInfo])
async def get_stores_info() -> list:
    """Get information about all data stores.

    TODO: Implement with repositories.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin endpoints not yet implemented",
    )


@router.post("/reindex-all", status_code=status.HTTP_202_ACCEPTED)
async def reindex_all_documents() -> dict:
    """Trigger reindexing of all documents.

    TODO: Implement with background task.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin endpoints not yet implemented",
    )


@router.post("/clear-cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache() -> None:
    """Clear all caches.

    TODO: Implement cache clearing.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin endpoints not yet implemented",
    )
