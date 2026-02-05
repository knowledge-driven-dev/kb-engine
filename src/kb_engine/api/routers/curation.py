"""Curation API endpoints for manual knowledge management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kb_engine.core.models.graph import EdgeType, NodeType

router = APIRouter(prefix="/curation")


class CreateNodeRequest(BaseModel):
    """Request to create a node in the knowledge graph."""

    name: str = Field(..., min_length=1, max_length=255)
    node_type: NodeType
    description: str | None = None
    properties: dict = Field(default_factory=dict)


class CreateEdgeRequest(BaseModel):
    """Request to create an edge in the knowledge graph."""

    source_node_id: UUID
    target_node_id: UUID
    edge_type: EdgeType
    name: str | None = None
    properties: dict = Field(default_factory=dict)


class NodeResponse(BaseModel):
    """Response for node operations."""

    id: UUID
    name: str
    node_type: NodeType
    description: str | None


class EdgeResponse(BaseModel):
    """Response for edge operations."""

    id: UUID
    source_id: UUID
    target_id: UUID
    edge_type: EdgeType
    name: str | None


@router.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(request: CreateNodeRequest) -> dict:
    """Manually create a node in the knowledge graph.

    TODO: Implement with graph repository.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Curation endpoints not yet implemented",
    )


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(node_id: UUID) -> dict:
    """Get a node by ID.

    TODO: Implement with graph repository.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Curation endpoints not yet implemented",
    )


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: UUID) -> None:
    """Delete a node.

    TODO: Implement with graph repository.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Curation endpoints not yet implemented",
    )


@router.post("/edges", response_model=EdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(request: CreateEdgeRequest) -> dict:
    """Manually create an edge in the knowledge graph.

    TODO: Implement with graph repository.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Curation endpoints not yet implemented",
    )


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(edge_id: UUID) -> None:
    """Delete an edge.

    TODO: Implement with graph repository.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Curation endpoints not yet implemented",
    )
