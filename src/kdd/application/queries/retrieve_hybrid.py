"""QRY-003 — RetrieveHybrid.

The primary query for AI agents.  Combines semantic (QRY-002), graph
(QRY-001), and lexical search.  Results fused with combined scoring.
Corresponds to ``POST /v1/retrieve/context``.

Spec: specs/02-behavior/queries/QRY-003-RetrieveHybrid.md

Fusion scoring priority:
- semantic + graph = highest
- semantic only = medium-high
- graph only = medium
- lexical only = low
"""

from __future__ import annotations

from dataclasses import dataclass

from kdd.domain.entities import GraphEdge, ScoredNode
from kdd.domain.enums import KDDKind, KDDLayer
from kdd.domain.ports import EmbeddingModel, GraphStore, VectorStore
from kdd.infrastructure.parsing.tokenization import count_tokens


@dataclass
class HybridQueryInput:
    query_text: str
    expand_graph: bool = True
    depth: int = 2
    include_kinds: list[KDDKind] | None = None
    include_layers: list[KDDLayer] | None = None
    respect_layers: bool = True
    min_score: float = 0.5
    limit: int = 10
    max_tokens: int = 8000


@dataclass
class HybridQueryResult:
    results: list[ScoredNode]
    graph_expansion: list[GraphEdge]
    total_results: int
    total_tokens: int
    warnings: list[str]


# Fusion score weights
_WEIGHT_SEMANTIC = 0.6
_WEIGHT_GRAPH = 0.3
_WEIGHT_LEXICAL = 0.1


def retrieve_hybrid(
    query: HybridQueryInput,
    graph_store: GraphStore,
    vector_store: VectorStore | None = None,
    embedding_model: EmbeddingModel | None = None,
) -> HybridQueryResult:
    """Execute a hybrid search combining semantic, graph, and lexical (QRY-003).

    Gracefully degrades:
    - No vector_store/embedding_model → graph + lexical only (warning)
    """
    if len(query.query_text.strip()) < 3:
        raise ValueError("QUERY_TOO_SHORT: query_text must be at least 3 characters")

    warnings: list[str] = []
    # Accumulators: node_id → {source: score}
    scores: dict[str, dict[str, float]] = {}

    # ── Phase 1: Semantic search ──────────────────────────────────────
    if vector_store is not None and embedding_model is not None:
        vectors = embedding_model.encode([query.query_text])
        matches = vector_store.search(
            vector=vectors[0],
            limit=query.limit * 3,
            min_score=query.min_score * 0.8,  # slightly lower threshold for fusion
        )
        for emb_id, score in matches:
            node_id = _emb_id_to_node_id(emb_id, graph_store)
            if node_id is None:
                continue
            scores.setdefault(node_id, {})["semantic"] = max(
                scores.get(node_id, {}).get("semantic", 0), score
            )
    else:
        warnings.append("NO_EMBEDDINGS: index is L1, semantic search skipped")

    # ── Phase 2: Lexical search ───────────────────────────────────────
    lexical_nodes = graph_store.text_search(query.query_text)
    for node in lexical_nodes:
        if _kind_layer_filter(node, query.include_kinds, query.include_layers):
            scores.setdefault(node.id, {})["lexical"] = 0.5

    # ── Phase 3: Graph expansion ──────────────────────────────────────
    all_graph_edges: list[GraphEdge] = []
    if query.expand_graph:
        # Expand from all nodes found so far
        seed_ids = list(scores.keys())
        for seed_id in seed_ids:
            if not graph_store.has_node(seed_id):
                continue
            nodes, edges = graph_store.traverse(
                root=seed_id,
                depth=query.depth,
                respect_layers=query.respect_layers,
            )
            all_graph_edges.extend(edges)
            for n in nodes:
                if n.id == seed_id:
                    continue
                if _kind_layer_filter(n, query.include_kinds, query.include_layers):
                    scores.setdefault(n.id, {})["graph"] = 0.5

    # ── Phase 4: Fusion scoring ───────────────────────────────────────
    fused: list[ScoredNode] = []
    for node_id, sources in scores.items():
        node = graph_store.get_node(node_id)
        if node is None:
            continue
        if not _kind_layer_filter(node, query.include_kinds, query.include_layers):
            continue

        score = _compute_fusion_score(sources)
        if score < query.min_score:
            continue

        match_source = _determine_match_source(sources)
        snippet = _build_snippet(node)
        fused.append(ScoredNode(
            node_id=node_id,
            score=score,
            snippet=snippet,
            match_source=match_source,
        ))

    # Sort by score, apply limit
    fused.sort(key=lambda s: s.score, reverse=True)

    # Token truncation
    final_results: list[ScoredNode] = []
    total_tokens = 0
    for scored in fused:
        snippet_tokens = count_tokens(scored.snippet or "")
        if total_tokens + snippet_tokens > query.max_tokens and final_results:
            break
        final_results.append(scored)
        total_tokens += snippet_tokens
        if len(final_results) >= query.limit:
            break

    # Deduplicate graph edges
    seen: set[tuple[str, str, str]] = set()
    unique_edges: list[GraphEdge] = []
    for e in all_graph_edges:
        key = (e.from_node, e.to_node, e.edge_type)
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    return HybridQueryResult(
        results=final_results,
        graph_expansion=unique_edges,
        total_results=len(final_results),
        total_tokens=total_tokens,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _emb_id_to_node_id(emb_id: str, graph_store: GraphStore) -> str | None:
    """Resolve an embedding ID to the owning node ID."""
    from kdd.application.extractors.base import KIND_PREFIX

    doc_id = emb_id.rsplit(":chunk-", 1)[0] if ":chunk-" in emb_id else emb_id.split(":")[0]

    for prefix in KIND_PREFIX.values():
        candidate = f"{prefix}:{doc_id}"
        if graph_store.has_node(candidate):
            return candidate
    if graph_store.has_node(doc_id):
        return doc_id
    return None


def _kind_layer_filter(node, include_kinds, include_layers) -> bool:
    if include_kinds and node.kind not in include_kinds:
        return False
    if include_layers and node.layer not in include_layers:
        return False
    return True


def _compute_fusion_score(sources: dict[str, float]) -> float:
    """Weighted fusion of multiple retrieval sources."""
    semantic = sources.get("semantic", 0)
    graph = sources.get("graph", 0)
    lexical = sources.get("lexical", 0)

    # Bonus for multi-source matches
    source_count = sum(1 for v in sources.values() if v > 0)
    bonus = 0.1 * (source_count - 1) if source_count > 1 else 0

    weighted = (
        semantic * _WEIGHT_SEMANTIC
        + graph * _WEIGHT_GRAPH
        + lexical * _WEIGHT_LEXICAL
        + bonus
    )

    # Normalize to [0, 1]
    return min(weighted / (_WEIGHT_SEMANTIC + _WEIGHT_GRAPH + _WEIGHT_LEXICAL + 0.2), 1.0)


def _determine_match_source(sources: dict[str, float]) -> str:
    has_semantic = sources.get("semantic", 0) > 0
    has_graph = sources.get("graph", 0) > 0
    has_lexical = sources.get("lexical", 0) > 0

    if has_semantic and has_graph:
        return "fusion"
    if has_semantic:
        return "semantic"
    if has_graph:
        return "graph"
    return "lexical"


def _build_snippet(node) -> str:
    title = node.indexed_fields.get("title", "")
    if title:
        return f"[{node.kind.value}] {title}"
    return f"[{node.kind.value}] {node.id}"
