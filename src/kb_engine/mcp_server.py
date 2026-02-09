"""MCP Server for kb-engine.

Exposes semantic search tools (kdd_search, kdd_related, kdd_list)
for AI agents via the Model Context Protocol.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import signal
import sys
from typing import Any

import click
from mcp.server.fastmcp import FastMCP

from kb_engine.core.interfaces.repositories import GraphRepository, TraceabilityRepository
from kb_engine.services.retrieval import RetrievalService

mcp = FastMCP("kb-engine", instructions="Semantic search over a KDD knowledge base.")

# --- Lazy-initialized services ---

_retrieval_service: RetrievalService | None = None
_graph_repo: GraphRepository | None = None
_traceability_repo: TraceabilityRepository | None = None
_factory: Any = None


async def _get_services() -> (
    tuple[RetrievalService, GraphRepository | None, TraceabilityRepository]
):
    """Lazy-init: create RepositoryFactory + repos + pipelines on first use."""
    global _retrieval_service, _graph_repo, _traceability_repo, _factory

    if _retrieval_service is not None and _traceability_repo is not None:
        return _retrieval_service, _graph_repo, _traceability_repo

    from kb_engine.config.settings import get_settings
    from kb_engine.embedding.config import EmbeddingConfig
    from kb_engine.pipelines.inference.pipeline import RetrievalPipeline
    from kb_engine.repositories.factory import RepositoryFactory

    settings = get_settings()
    _factory = RepositoryFactory(settings)

    traceability = await _factory.get_traceability_repository()
    vector = await _factory.get_vector_repository()
    graph = await _factory.get_graph_repository()

    embedding_config = EmbeddingConfig(
        provider=settings.embedding_provider,
        local_model_name=settings.local_embedding_model,
        openai_model=settings.openai_embedding_model,
    )

    retrieval_pipeline = RetrievalPipeline(
        traceability_repo=traceability,
        vector_repo=vector,
        graph_repo=graph,
        embedding_config=embedding_config,
    )

    _retrieval_service = RetrievalService(pipeline=retrieval_pipeline)
    _graph_repo = graph
    _traceability_repo = traceability

    return _retrieval_service, _graph_repo, _traceability_repo


# --- Cleanup ---


def _cleanup() -> None:
    """Close the factory on exit."""
    if _factory is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_factory.close())
            else:
                loop.run_until_complete(_factory.close())
        except Exception:
            pass


atexit.register(_cleanup)


def _signal_handler(sig: int, frame: Any) -> None:
    _cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# --- MCP Tools ---


@mcp.tool()
async def kdd_search(
    query: str,
    limit: int = 5,
    mode: str = "vector",
    chunk_types: list[str] | None = None,
    domains: list[str] | None = None,
    tags: list[str] | None = None,
    score_threshold: float | None = None,
) -> str:
    """Search the knowledge base semantically.

    Returns document references with URLs pointing to the matching sections.
    Use this to find documentation, ADRs, design challenges, or any indexed content.

    Args:
        query: Natural language search query.
        limit: Maximum number of results (default 5).
        mode: Retrieval mode - "vector" (semantic), "graph" (knowledge graph), or "hybrid" (both).
        chunk_types: Filter by chunk types (e.g. ["header", "paragraph"]).
        domains: Filter by document domains.
        tags: Filter by document tags.
        score_threshold: Minimum relevance score (0.0-1.0).
    """
    from kb_engine.core.models.search import RetrievalMode, SearchFilters

    retrieval, _, _ = await _get_services()

    # Map mode string to enum
    mode_map = {
        "vector": RetrievalMode.VECTOR,
        "graph": RetrievalMode.GRAPH,
        "hybrid": RetrievalMode.HYBRID,
    }
    retrieval_mode = mode_map.get(mode.lower(), RetrievalMode.VECTOR)

    filters = None
    if chunk_types or domains or tags:
        filters = SearchFilters(
            chunk_types=chunk_types,
            domains=domains,
            tags=tags,
        )

    response = await retrieval.search(
        query=query,
        mode=retrieval_mode,
        limit=limit,
        filters=filters,
        score_threshold=score_threshold,
    )

    results = []
    for ref in response.references:
        result = {
            "url": ref.url,
            "title": ref.title,
            "section": ref.section_title,
            "score": round(ref.score, 4),
            "snippet": ref.snippet[:200] if ref.snippet else "",
            "type": ref.chunk_type,
            "domain": ref.domain,
            "retrieval_mode": ref.retrieval_mode.value,
        }
        # Include graph metadata if present
        if ref.metadata.get("graph_relationships"):
            result["graph"] = {
                "node_name": ref.metadata.get("graph_node_name"),
                "node_type": ref.metadata.get("graph_node_type"),
                "relationships": ref.metadata.get("graph_relationships"),
            }
        results.append(result)

    return json.dumps({
        "query": response.query,
        "mode": retrieval_mode.value,
        "total": response.total_count,
        "results": results,
    })


@mcp.tool()
async def kdd_related(
    entity: str,
    depth: int = 1,
    edge_types: list[str] | None = None,
    limit: int = 20,
) -> str:
    """Find entities related to a given entity in the knowledge graph.

    Traverses the knowledge graph to find connected concepts, entities, and events.

    Args:
        entity: Name or pattern of the entity to search for.
        depth: How many hops to traverse (default 1).
        edge_types: Filter by relationship types (e.g. ["REFERENCES", "CONTAINS"]).
        limit: Maximum number of related entities to return.
    """
    _, graph_repo, traceability = await _get_services()

    if graph_repo is None:
        return json.dumps({
            "error": "Graph store is not available. Configure graph_store in settings.",
        })

    nodes = await graph_repo.find_nodes(name_pattern=entity)
    if not nodes:
        return json.dumps({
            "entity": entity,
            "related": [],
            "message": f"No entity found matching '{entity}'.",
        })

    start_node = nodes[0]
    triples = await graph_repo.traverse(
        start_node_id=start_node.id,
        max_hops=depth,
        edge_types=edge_types,
    )

    related = []
    seen_ids = set()
    for source, edge, target in triples[:limit]:
        if target.id in seen_ids:
            continue
        seen_ids.add(target.id)

        doc_url = None
        if target.source_document_id and traceability:
            doc = await traceability.get_document(target.source_document_id)
            if doc:
                doc_url = f"file://{doc.source_path}" if doc.source_path else None

        related.append({
            "name": target.name,
            "type": target.node_type.value if hasattr(target.node_type, "value") else str(target.node_type),
            "relationship": edge.edge_type.value if hasattr(edge.edge_type, "value") else str(edge.edge_type),
            "confidence": round(edge.confidence, 4),
            "document_url": doc_url,
        })

    return json.dumps({
        "entity": {
            "name": start_node.name,
            "type": start_node.node_type.value if hasattr(start_node.node_type, "value") else str(start_node.node_type),
        },
        "related": related,
    })


@mcp.tool()
async def kdd_list(
    kind: str | None = None,
    domain: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> str:
    """List indexed documents in the knowledge base.

    Returns a summary of all indexed documents with metadata.

    Args:
        kind: Filter by document kind (from KDD metadata, e.g. "adr", "challenge").
        domain: Filter by document domain.
        status: Filter by document status (e.g. "indexed", "pending").
        limit: Maximum number of documents to return.
    """
    from kb_engine.core.models.search import SearchFilters

    _, _, traceability = await _get_services()

    filters = None
    if domain:
        filters = SearchFilters(domains=[domain])

    docs = await traceability.list_documents(filters=filters, limit=limit)

    # Apply in-memory filters that the repository doesn't support directly
    if kind:
        docs = [d for d in docs if d.metadata.get("kind") == kind]
    if status:
        docs = [d for d in docs if d.status.value == status]

    results = []
    for doc in docs:
        chunks = await traceability.get_chunks_by_document(doc.id)
        results.append({
            "path": doc.relative_path or doc.source_path,
            "title": doc.title,
            "kind": doc.metadata.get("kind"),
            "domain": doc.domain,
            "status": doc.status.value,
            "chunks": len(chunks),
            "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
        })

    return json.dumps({"total": len(results), "documents": results})


# --- CLI fallback ---


@click.group()
def mcp_cli() -> None:
    """KB-Engine MCP Server CLI (for testing)."""
    pass


@mcp_cli.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Max results")
@click.option("--mode", "-m", type=click.Choice(["vector", "graph", "hybrid"]), default="vector", help="Retrieval mode")
def cli_search(query: str, limit: int, mode: str) -> None:
    """Search the knowledge base."""
    result = asyncio.run(kdd_search(query=query, limit=limit, mode=mode))
    data = json.loads(result)
    click.echo(json.dumps(data, indent=2))


@mcp_cli.command("related")
@click.argument("entity")
@click.option("--depth", "-d", default=1, help="Traversal depth")
def cli_related(entity: str, depth: int) -> None:
    """Find related entities."""
    result = asyncio.run(kdd_related(entity=entity, depth=depth))
    data = json.loads(result)
    click.echo(json.dumps(data, indent=2))


@mcp_cli.command("list")
@click.option("--kind", "-k", default=None, help="Filter by document kind")
@click.option("--domain", "-d", default=None, help="Filter by domain")
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--limit", "-l", default=20, help="Max results")
def cli_list(kind: str | None, domain: str | None, status: str | None, limit: int) -> None:
    """List indexed documents."""
    result = asyncio.run(kdd_list(kind=kind, domain=domain, status=status, limit=limit))
    data = json.loads(result)
    click.echo(json.dumps(data, indent=2))


# --- Entry points ---


def main() -> None:
    """Entry point for the kb-mcp script."""
    mcp.run()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.argv.pop(1)
        mcp_cli()
    else:
        mcp.run()
