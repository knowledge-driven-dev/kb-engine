"""CMD-002 — IndexIncremental command.

Uses git diff to identify changed files since the last indexed commit,
then processes only new/modified/deleted files:
- New files → index via CMD-001
- Modified → delete old artifacts + re-index via CMD-001
- Deleted → cascade delete artifacts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from kdd.application.commands.index_document import IndexResult, index_document
from kdd.application.extractors.registry import ExtractorRegistry
from kdd.domain.entities import IndexManifest, IndexStats
from kdd.domain.enums import IndexLevel
from kdd.domain.ports import ArtifactStore, EmbeddingModel, EventBus
from kdd.infrastructure.git.diff import get_current_commit, get_diff, scan_files

logger = logging.getLogger(__name__)


@dataclass
class IncrementalResult:
    """Result of an incremental indexing run."""

    indexed: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[IndexResult] = field(default_factory=list)
    is_full_reindex: bool = False


def _index_file(
    rel_path: str,
    *,
    repo_root: Path,
    specs_root: Path,
    registry: ExtractorRegistry,
    artifact_store: ArtifactStore,
    event_bus: EventBus | None,
    embedding_model: EmbeddingModel | None,
    index_level: IndexLevel,
    domain: str | None,
) -> IndexResult:
    """Index a single file given its repo-relative path."""
    file_path = repo_root / rel_path
    return index_document(
        file_path,
        specs_root=specs_root,
        registry=registry,
        artifact_store=artifact_store,
        event_bus=event_bus,
        embedding_model=embedding_model,
        index_level=index_level,
        domain=domain,
    )


def index_incremental(
    specs_root: Path,
    *,
    repo_root: Path | None = None,
    registry: ExtractorRegistry,
    artifact_store: ArtifactStore,
    event_bus: EventBus | None = None,
    embedding_model: EmbeddingModel | None = None,
    index_level: IndexLevel = IndexLevel.L1,
    include_patterns: list[str] | None = None,
    domain: str | None = None,
) -> IncrementalResult:
    """Run incremental indexing based on git diff.

    If no previous manifest exists, performs a full index of all matching files.

    Args:
        specs_root: Root directory of specs (used to compute relative paths).
        repo_root: Git repository root. Defaults to ``specs_root`` if not given.
        registry: Extractor registry.
        artifact_store: Store for reading/writing artifacts.
        event_bus: Optional event bus.
        embedding_model: Optional embedding model for L2+.
        index_level: Target index level.
        include_patterns: Glob patterns for files to include (default: ``["**/*.md"]``).
        domain: Optional domain override.
    """
    if include_patterns is None:
        include_patterns = ["**/*.md"]
    if repo_root is None:
        repo_root = specs_root

    result = IncrementalResult()

    # Read existing manifest
    manifest = artifact_store.read_manifest()
    current_commit = get_current_commit(repo_root)

    common_kwargs = dict(
        repo_root=repo_root,
        specs_root=specs_root,
        registry=registry,
        artifact_store=artifact_store,
        event_bus=event_bus,
        embedding_model=embedding_model,
        index_level=index_level,
        domain=domain,
    )

    if manifest is None or manifest.git_commit is None:
        # No previous index — full reindex
        result.is_full_reindex = True
        # scan_files returns paths relative to cwd (repo_root)
        all_files = scan_files(repo_root, include_patterns=include_patterns)
        for rel_path in all_files:
            r = _index_file(rel_path, **common_kwargs)
            result.results.append(r)
            if r.success:
                result.indexed += 1
            elif r.skipped_reason:
                result.skipped += 1
            else:
                result.errors += 1
    else:
        # Incremental: only changed files
        # get_diff returns paths relative to git root
        diff = get_diff(
            repo_root,
            manifest.git_commit,
            include_patterns=include_patterns,
        )

        # Process new files
        for rel_path in diff.added:
            r = _index_file(rel_path, **common_kwargs)
            result.results.append(r)
            if r.success:
                result.indexed += 1
            elif r.skipped_reason:
                result.skipped += 1
            else:
                result.errors += 1

        # Process modified files: delete old + re-index
        for rel_path in diff.modified:
            artifact_store.delete_document_artifacts(rel_path)
            r = _index_file(rel_path, **common_kwargs)
            result.results.append(r)
            if r.success:
                result.indexed += 1
            elif r.skipped_reason:
                result.skipped += 1
            else:
                result.errors += 1

        # Process deleted files: cascade delete
        for rel_path in diff.deleted:
            artifact_store.delete_document_artifacts(rel_path)
            result.deleted += 1

    # Update manifest
    total_nodes = sum(1 for r in result.results if r.success)
    total_edges = sum(r.edge_count for r in result.results if r.success)
    total_embeddings = sum(r.embedding_count for r in result.results if r.success)

    new_manifest = IndexManifest(
        version="1.0.0",
        kdd_version="1.0.0",
        indexed_by="kdd-cli",
        index_level=index_level,
        git_commit=current_commit,
        indexed_at=datetime.now(),
        stats=IndexStats(
            nodes=total_nodes,
            edges=total_edges,
            embeddings=total_embeddings,
        ),
        domains=[domain] if domain else [],
    )
    artifact_store.write_manifest(new_manifest)

    return result
