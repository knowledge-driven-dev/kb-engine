"""CMD-003 — EnrichWithAgent command.

Enriches an existing GraphNode using the developer's AI agent (L3).
Completely optional — requires API key and L2+ index.

Spec: specs/02-behavior/commands/CMD-003-EnrichWithAgent.md
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from kdd.domain.entities import GraphEdge, GraphNode
from kdd.domain.ports import AgentClient, ArtifactStore

logger = logging.getLogger(__name__)


@dataclass
class EnrichResult:
    success: bool
    enrichment: dict | None = None
    implicit_edges: int = 0
    error: str | None = None


def enrich_with_agent(
    node_id: str,
    *,
    artifact_store: ArtifactStore,
    agent_client: AgentClient,
    specs_root: Path,
) -> EnrichResult:
    """Enrich a graph node using an AI agent (CMD-003 / UC-003).

    Reads the source document, builds a prompt with existing graph context,
    and asks the agent to produce an improved summary + implicit relations.
    """
    # 1. Find the node
    node = artifact_store.read_node(node_id)
    if node is None:
        return EnrichResult(success=False, error=f"NODE_NOT_FOUND: {node_id}")

    # 2. Read source document
    source_path = specs_root / node.source_file
    if not source_path.exists():
        return EnrichResult(success=False, error=f"DOCUMENT_NOT_FOUND: {node.source_file}")

    content = source_path.read_text(encoding="utf-8")

    # 3. Build context (document + existing edges)
    edges = artifact_store.read_edges()
    related_edges = [
        e for e in edges if e.from_node == node_id or e.to_node == node_id
    ]
    context = _build_context(node, content, related_edges)

    # 4. Call agent
    try:
        enrichment = agent_client.enrich(node, context)
    except Exception as e:
        return EnrichResult(success=False, error=f"AGENT_ERROR: {e}")

    # 5. Store enrichment
    enrichments_dir = Path(artifact_store.root) / "enrichments" if hasattr(artifact_store, "root") else None
    if enrichments_dir:
        enrichments_dir.mkdir(parents=True, exist_ok=True)
        doc_id = node_id.split(":", 1)[-1] if ":" in node_id else node_id
        out_path = enrichments_dir / f"{doc_id}.json"
        out_path.write_text(
            json.dumps(enrichment, indent=2, default=str),
            encoding="utf-8",
        )

    # 6. Extract implicit relations from enrichment
    implicit_edges: list[GraphEdge] = []
    for rel in enrichment.get("implicit_relations", []):
        implicit_edges.append(GraphEdge(
            from_node=node_id,
            to_node=rel.get("target", ""),
            edge_type=rel.get("type", "WIKI_LINK"),
            source_file=node.source_file,
            extraction_method="implicit",
            metadata={"agent": "enrichment"},
        ))

    if implicit_edges:
        artifact_store.append_edges(implicit_edges)

    return EnrichResult(
        success=True,
        enrichment=enrichment,
        implicit_edges=len(implicit_edges),
    )


def _build_context(
    node: GraphNode,
    document_content: str,
    related_edges: list[GraphEdge],
) -> str:
    """Build a context string for the agent prompt."""
    parts = [
        f"# Node: {node.id}",
        f"Kind: {node.kind.value}",
        f"Layer: {node.layer.value}",
        "",
        "## Document Content",
        document_content[:5000],  # Truncate for token budget
        "",
        "## Existing Relations",
    ]
    for edge in related_edges[:20]:
        direction = "->" if edge.from_node == node.id else "<-"
        other = edge.to_node if edge.from_node == node.id else edge.from_node
        parts.append(f"  {direction} {other} [{edge.edge_type}]")

    return "\n".join(parts)
