"""Models for extraction results."""

from typing import Any

from pydantic import BaseModel, Field

from kb_engine.core.models.graph import EdgeType, NodeType


class ExtractedNode(BaseModel):
    """An entity extracted from content before graph persistence."""

    name: str
    node_type: NodeType
    description: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

    # Extraction metadata
    confidence: float = 1.0
    extraction_method: str = "unknown"
    source_text: str | None = None

    class Config:
        frozen = False


class ExtractedEdge(BaseModel):
    """A relationship extracted from content before graph persistence."""

    source_name: str
    target_name: str
    edge_type: EdgeType
    name: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

    # Extraction metadata
    confidence: float = 1.0
    extraction_method: str = "unknown"
    source_text: str | None = None

    class Config:
        frozen = False
