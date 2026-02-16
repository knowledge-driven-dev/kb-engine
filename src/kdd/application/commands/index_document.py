"""CMD-001 — IndexDocument command.

Processes a single KDD spec file through the full indexing pipeline:
1. Read file and extract front-matter
2. Route document via BR-DOCUMENT-001
3. Extract node + edges via kind-specific extractor
4. Validate layer dependencies (BR-LAYER-001)
5. Optional L2: chunk + embed (BR-EMBEDDING-001)
6. Write artifacts to ArtifactStore
7. Emit domain events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from kdd.application.chunking import chunk_document
from kdd.application.extractors.registry import ExtractorRegistry
from kdd.domain.entities import Embedding, GraphEdge, GraphNode, KDDDocument
from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer
from kdd.domain.events import DocumentDetected, DocumentIndexed, DocumentParsed
from kdd.domain.ports import ArtifactStore, EmbeddingModel, EventBus
from kdd.domain.rules import detect_layer, route_document
from kdd.infrastructure.parsing.hashing import compute_content_hash
from kdd.infrastructure.parsing.markdown import (
    extract_frontmatter,
    parse_markdown_sections,
)
from kdd.infrastructure.parsing.wiki_links import extract_wiki_link_targets

logger = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """Result of indexing a single document."""

    success: bool
    node_id: str | None = None
    edge_count: int = 0
    embedding_count: int = 0
    skipped_reason: str | None = None
    warning: str | None = None


def index_document(
    file_path: Path,
    *,
    specs_root: Path,
    registry: ExtractorRegistry,
    artifact_store: ArtifactStore,
    event_bus: EventBus | None = None,
    embedding_model: EmbeddingModel | None = None,
    index_level: IndexLevel = IndexLevel.L1,
    domain: str | None = None,
) -> IndexResult:
    """Index a single KDD spec file.

    Args:
        file_path: Absolute path to the spec file.
        specs_root: Root directory of specs (for relative path computation).
        registry: Extractor registry with all kind extractors.
        artifact_store: Store to write artifacts to.
        event_bus: Optional event bus for domain events.
        embedding_model: Optional embedding model for L2+ indexing.
        index_level: Target index level (L1, L2, L3).
        domain: Optional domain override.

    Returns:
        IndexResult with success status and metadata.
    """
    start = datetime.now()

    # 1. Read file
    try:
        content = file_path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError) as e:
        return IndexResult(success=False, skipped_reason=f"File error: {e}")

    # 2. Extract front-matter and route
    front_matter, body = extract_frontmatter(content)
    relative_path = str(file_path.relative_to(specs_root))
    route = route_document(front_matter, relative_path)

    if route.kind is None:
        return IndexResult(success=False, skipped_reason="No valid kind in front-matter")

    # 3. Find extractor
    extractor = registry.get(route.kind)
    if extractor is None:
        return IndexResult(
            success=False,
            skipped_reason=f"No extractor registered for kind '{route.kind.value}'",
        )

    # 4. Build KDDDocument
    sections = parse_markdown_sections(body)
    wiki_links = extract_wiki_link_targets(body)
    layer = detect_layer(relative_path) or KDDLayer.DOMAIN
    doc_id = front_matter.get("id", file_path.stem)
    source_hash = compute_content_hash(content)

    # Emit DocumentDetected
    if event_bus:
        event_bus.publish(DocumentDetected(
            source_path=relative_path,
            source_hash=source_hash,
            kind=route.kind,
            layer=layer,
            detected_at=start,
        ))

    document = KDDDocument(
        id=doc_id,
        kind=route.kind,
        source_path=relative_path,
        source_hash=source_hash,
        layer=layer,
        front_matter=front_matter,
        sections=sections,
        wiki_links=wiki_links,
        domain=domain,
    )

    # Emit DocumentParsed
    if event_bus:
        event_bus.publish(DocumentParsed(
            source_path=relative_path,
            kind=route.kind,
            document_id=doc_id,
            front_matter=front_matter,
            section_count=len(sections),
            wiki_link_count=len(wiki_links),
            parsed_at=datetime.now(),
        ))

    # 5. Extract node + edges
    node = extractor.extract_node(document)
    edges = extractor.extract_edges(document)

    # 6. Write node + edges to artifact store
    artifact_store.write_node(node)
    if edges:
        artifact_store.append_edges(edges)

    # 7. Optional L2: chunk + embed
    embeddings: list[Embedding] = []
    if index_level in (IndexLevel.L2, IndexLevel.L3) and embedding_model is not None:
        chunks = chunk_document(document)
        if chunks:
            texts = [c.context_text for c in chunks]
            vectors = embedding_model.encode(texts)
            now = datetime.now()
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                embeddings.append(Embedding(
                    id=chunk.chunk_id,
                    document_id=doc_id,
                    document_kind=route.kind,
                    section_path=chunk.section_heading,
                    chunk_index=i,
                    raw_text=chunk.content,
                    context_text=chunk.context_text,
                    vector=vector,
                    model=embedding_model.model_name,
                    dimensions=embedding_model.dimensions,
                    text_hash=compute_content_hash(chunk.content),
                    generated_at=now,
                ))
            artifact_store.write_embeddings(embeddings)

    # 8. Emit DocumentIndexed
    duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    if event_bus:
        event_bus.publish(DocumentIndexed(
            source_path=relative_path,
            kind=route.kind,
            document_id=doc_id,
            node_id=node.id,
            edge_count=len(edges),
            embedding_count=len(embeddings),
            index_level=index_level,
            duration_ms=duration_ms,
            indexed_at=datetime.now(),
        ))

    return IndexResult(
        success=True,
        node_id=node.id,
        edge_count=len(edges),
        embedding_count=len(embeddings),
        warning=route.warning,
    )
