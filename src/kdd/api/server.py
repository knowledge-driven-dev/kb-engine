"""KDD REST API — FastAPI server.

Provides the ``/v1/retrieve/*`` endpoints for AI agent integration.

Endpoints:
  POST /v1/retrieve/search    (QRY-002: semantic search)
  POST /v1/retrieve/context   (QRY-003: hybrid search — primary endpoint)
  GET  /v1/retrieve/graph     (QRY-001: graph traversal)
  GET  /v1/retrieve/impact    (QRY-004: impact analysis)
  GET  /v1/retrieve/coverage  (QRY-005: governance coverage)
  GET  /v1/retrieve/layer-violations  (QRY-006: layer violations)
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from kdd.container import Container, create_container

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KDD Retrieval API",
    version="1.0.0",
    description="Knowledge-Driven Development retrieval engine.",
)


def _get_container() -> Container:
    """Dependency injection: resolve the global container.

    Override ``app.dependency_overrides[_get_container]`` in tests.
    """
    if not hasattr(app.state, "container"):
        raise HTTPException(503, "Index not loaded. Start server with --specs-path.")
    return app.state.container


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query_text: str = Field(..., min_length=3)
    include_kinds: list[str] | None = None
    include_layers: list[str] | None = None
    min_score: float = 0.7
    limit: int = 10


class ContextRequest(BaseModel):
    query_text: str = Field(..., min_length=3)
    expand_graph: bool = True
    depth: int = 2
    include_kinds: list[str] | None = None
    include_layers: list[str] | None = None
    respect_layers: bool = True
    min_score: float = 0.5
    limit: int = 10
    max_tokens: int = 8000


class ScoredNodeResponse(BaseModel):
    node_id: str
    score: float
    snippet: str | None = None
    match_source: str


class SearchResponse(BaseModel):
    results: list[ScoredNodeResponse]
    total_results: int
    embedding_model: str | None = None


class ContextResponse(BaseModel):
    results: list[ScoredNodeResponse]
    total_results: int
    total_tokens: int
    warnings: list[str]


class GraphNodeResponse(BaseModel):
    node_id: str
    score: float
    snippet: str | None = None
    match_source: str = "graph"


class GraphResponse(BaseModel):
    center_node: str | None
    related_nodes: list[GraphNodeResponse]
    total_nodes: int
    total_edges: int


class AffectedNodeResponse(BaseModel):
    node_id: str
    kind: str
    edge_type: str
    impact_description: str


class TransitiveResponse(BaseModel):
    node_id: str
    kind: str
    path: list[str]


class ScenarioResponse(BaseModel):
    node_id: str
    scenario_name: str
    reason: str


class ImpactResponse(BaseModel):
    analyzed_node: str | None
    directly_affected: list[AffectedNodeResponse]
    transitively_affected: list[TransitiveResponse]
    scenarios_to_rerun: list[ScenarioResponse]
    total_directly: int
    total_transitively: int


class CoverageCategoryResponse(BaseModel):
    name: str
    status: str
    found: list[str]


class CoverageResponse(BaseModel):
    node_id: str
    coverage_percent: float
    categories: list[CoverageCategoryResponse]


class ViolationResponse(BaseModel):
    from_node: str
    to_node: str
    from_layer: str
    to_layer: str
    edge_type: str


class ViolationsResponse(BaseModel):
    violations: list[ViolationResponse]
    total_violations: int
    total_edges_analyzed: int
    violation_rate: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/v1/retrieve/search", response_model=SearchResponse)
def retrieve_search(
    body: SearchRequest,
    container: Container = Depends(_get_container),
):
    """QRY-002: Semantic search over embeddings."""
    if container.embedding_model is None or container.vector_store is None:
        raise HTTPException(400, "Semantic search requires L2 index (embeddings).")

    if not container.ensure_loaded():
        raise HTTPException(503, "Index not loaded.")

    from kdd.application.queries.retrieve_semantic import SemanticQueryInput, retrieve_semantic
    from kdd.domain.enums import KDDKind, KDDLayer

    include_kinds = [KDDKind(k) for k in body.include_kinds] if body.include_kinds else None
    include_layers = [KDDLayer(l) for l in body.include_layers] if body.include_layers else None

    try:
        result = retrieve_semantic(
            SemanticQueryInput(
                query_text=body.query_text,
                include_kinds=include_kinds,
                include_layers=include_layers,
                min_score=body.min_score,
                limit=body.limit,
            ),
            container.embedding_model,
            container.vector_store,
            container.graph_store,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return SearchResponse(
        results=[
            ScoredNodeResponse(
                node_id=r.node_id, score=round(r.score, 4),
                snippet=r.snippet, match_source=r.match_source,
            )
            for r in result.results
        ],
        total_results=result.total_results,
        embedding_model=result.embedding_model,
    )


@app.post("/v1/retrieve/context", response_model=ContextResponse)
def retrieve_context(
    body: ContextRequest,
    container: Container = Depends(_get_container),
):
    """QRY-003: Hybrid search (primary endpoint for AI agents)."""
    if not container.ensure_loaded():
        raise HTTPException(503, "Index not loaded.")

    from kdd.application.queries.retrieve_hybrid import HybridQueryInput, retrieve_hybrid
    from kdd.domain.enums import KDDKind, KDDLayer

    include_kinds = [KDDKind(k) for k in body.include_kinds] if body.include_kinds else None
    include_layers = [KDDLayer(l) for l in body.include_layers] if body.include_layers else None

    try:
        result = retrieve_hybrid(
            HybridQueryInput(
                query_text=body.query_text,
                expand_graph=body.expand_graph,
                depth=body.depth,
                include_kinds=include_kinds,
                include_layers=include_layers,
                respect_layers=body.respect_layers,
                min_score=body.min_score,
                limit=body.limit,
                max_tokens=body.max_tokens,
            ),
            container.graph_store,
            container.vector_store,
            container.embedding_model,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return ContextResponse(
        results=[
            ScoredNodeResponse(
                node_id=r.node_id, score=round(r.score, 4),
                snippet=r.snippet, match_source=r.match_source,
            )
            for r in result.results
        ],
        total_results=result.total_results,
        total_tokens=result.total_tokens,
        warnings=result.warnings,
    )


@app.get("/v1/retrieve/graph", response_model=GraphResponse)
def retrieve_graph(
    node_id: str,
    depth: int = 2,
    edge_type: Annotated[list[str] | None, Query()] = None,
    container: Container = Depends(_get_container),
):
    """QRY-001: Graph traversal from a root node."""
    if not container.ensure_loaded():
        raise HTTPException(503, "Index not loaded.")

    from kdd.application.queries.retrieve_graph import GraphQueryInput, retrieve_by_graph

    try:
        result = retrieve_by_graph(
            GraphQueryInput(root_node=node_id, depth=depth, edge_types=edge_type),
            container.graph_store,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    return GraphResponse(
        center_node=result.center_node.id if result.center_node else None,
        related_nodes=[
            GraphNodeResponse(
                node_id=r.node_id, score=round(r.score, 4), snippet=r.snippet,
            )
            for r in result.related_nodes
        ],
        total_nodes=result.total_nodes,
        total_edges=result.total_edges,
    )


@app.get("/v1/retrieve/impact", response_model=ImpactResponse)
def retrieve_impact(
    node_id: str,
    depth: int = 3,
    container: Container = Depends(_get_container),
):
    """QRY-004: Impact analysis for a node."""
    if not container.ensure_loaded():
        raise HTTPException(503, "Index not loaded.")

    from kdd.application.queries.retrieve_impact import ImpactQueryInput, retrieve_impact

    try:
        result = retrieve_impact(
            ImpactQueryInput(node_id=node_id, depth=depth),
            container.graph_store,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    return ImpactResponse(
        analyzed_node=result.analyzed_node.id if result.analyzed_node else None,
        directly_affected=[
            AffectedNodeResponse(
                node_id=a.node_id, kind=a.kind,
                edge_type=a.edge_type, impact_description=a.impact_description,
            )
            for a in result.directly_affected
        ],
        transitively_affected=[
            TransitiveResponse(node_id=t.node_id, kind=t.kind, path=t.path)
            for t in result.transitively_affected
        ],
        scenarios_to_rerun=[
            ScenarioResponse(
                node_id=s.node_id, scenario_name=s.scenario_name, reason=s.reason,
            )
            for s in result.scenarios_to_rerun
        ],
        total_directly=result.total_directly,
        total_transitively=result.total_transitively,
    )


@app.get("/v1/retrieve/coverage", response_model=CoverageResponse)
def retrieve_coverage(
    node_id: str,
    container: Container = Depends(_get_container),
):
    """QRY-005: Governance coverage analysis."""
    if not container.ensure_loaded():
        raise HTTPException(503, "Index not loaded.")

    from kdd.application.queries.retrieve_coverage import CoverageQueryInput, retrieve_coverage

    try:
        result = retrieve_coverage(
            CoverageQueryInput(node_id=node_id),
            container.graph_store,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    return CoverageResponse(
        node_id=node_id,
        coverage_percent=result.coverage_percent,
        categories=[
            CoverageCategoryResponse(name=c.name, status=c.status, found=c.found)
            for c in result.categories
        ],
    )


@app.get("/v1/retrieve/layer-violations", response_model=ViolationsResponse)
def retrieve_violations(
    container: Container = Depends(_get_container),
):
    """QRY-006: List all layer dependency violations."""
    if not container.ensure_loaded():
        raise HTTPException(503, "Index not loaded.")

    from kdd.application.queries.retrieve_violations import (
        ViolationsQueryInput,
        retrieve_violations,
    )

    result = retrieve_violations(ViolationsQueryInput(), container.graph_store)

    return ViolationsResponse(
        violations=[
            ViolationResponse(
                from_node=v.from_node, to_node=v.to_node,
                from_layer=v.from_layer.value, to_layer=v.to_layer.value,
                edge_type=v.edge_type,
            )
            for v in result.violations
        ],
        total_violations=result.total_violations,
        total_edges_analyzed=result.total_edges_analyzed,
        violation_rate=result.violation_rate,
    )


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------


def create_app(specs_path: str = ".", index_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI app with a loaded container."""
    specs_root = Path(specs_path).resolve()
    idx_path = Path(index_path) if index_path else None
    container = create_container(specs_root, idx_path)
    container.ensure_loaded()
    app.state.container = container
    return app
