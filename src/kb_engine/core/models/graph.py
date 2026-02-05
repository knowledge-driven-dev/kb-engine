"""Graph models for knowledge graph representation."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph (ADR-0003)."""

    ENTITY = "entity"
    USE_CASE = "use_case"
    RULE = "rule"
    PROCESS = "process"
    ACTOR = "actor"
    SYSTEM = "system"
    CONCEPT = "concept"
    DOCUMENT = "document"
    CHUNK = "chunk"


class EdgeType(str, Enum):
    """Types of edges in the knowledge graph (ADR-0003)."""

    # Structural relationships
    CONTAINS = "CONTAINS"
    PART_OF = "PART_OF"
    REFERENCES = "REFERENCES"

    # Domain relationships
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"
    TRIGGERS = "TRIGGERS"
    USES = "USES"
    PRODUCES = "PRODUCES"

    # Actor relationships
    PERFORMS = "PERFORMS"
    OWNS = "OWNS"

    # Semantic relationships
    SIMILAR_TO = "SIMILAR_TO"
    CONTRADICTS = "CONTRADICTS"
    EXTENDS = "EXTENDS"


class Node(BaseModel):
    """A node in the knowledge graph.

    Nodes represent entities, concepts, or structural elements
    extracted from documents.
    """

    id: UUID = Field(default_factory=uuid4)
    external_id: str | None = None
    name: str
    node_type: NodeType
    description: str | None = None

    # Source traceability
    source_document_id: UUID | None = None
    source_chunk_id: UUID | None = None

    # Properties
    properties: dict[str, Any] = Field(default_factory=dict)

    # Extraction metadata
    confidence: float = 1.0
    extraction_method: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = False


class Edge(BaseModel):
    """An edge in the knowledge graph.

    Edges represent relationships between nodes.
    """

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    edge_type: EdgeType
    name: str | None = None

    # Properties
    properties: dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0

    # Source traceability
    source_document_id: UUID | None = None
    source_chunk_id: UUID | None = None

    # Extraction metadata
    confidence: float = 1.0
    extraction_method: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = False
