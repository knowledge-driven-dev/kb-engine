"""Index loader — reads .kdd-index/ artifacts into memory stores.

Bridges the write side (ArtifactStore on disk) with the read side
(GraphStore + VectorStore in memory).  Caches the loaded state and
reloads when the manifest changes.
"""

from __future__ import annotations

from kdd.domain.ports import ArtifactStore, GraphStore, VectorStore


class IndexLoader:
    """Loads index artifacts into in-memory stores for querying.

    Usage::

        loader = IndexLoader(artifact_store, graph_store, vector_store)
        loader.load()  # populates graph + vector stores
        # … run queries against graph_store / vector_store …
    """

    def __init__(
        self,
        artifact_store: ArtifactStore,
        graph_store: GraphStore,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._artifacts = artifact_store
        self._graph = graph_store
        self._vector = vector_store
        self._loaded_manifest_hash: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded_manifest_hash is not None

    def load(self, *, force: bool = False) -> bool:
        """Load artifacts into memory stores.

        Returns True if stores were (re)loaded, False if the cache was still
        valid and *force* was not requested.
        """
        manifest = self._artifacts.read_manifest()
        if manifest is None:
            return False

        # Cache check: skip reload if manifest hasn't changed
        manifest_hash = f"{manifest.indexed_at}:{manifest.stats.nodes}:{manifest.stats.edges}"
        if not force and self._loaded_manifest_hash == manifest_hash:
            return False

        # Load graph
        nodes = self._artifacts.read_all_nodes()
        edges = self._artifacts.read_edges()
        self._graph.load(nodes, edges)

        # Load vectors (optional — L2+ only)
        if self._vector is not None:
            embeddings = self._artifacts.read_all_embeddings()
            if embeddings:
                self._vector.load(embeddings)

        self._loaded_manifest_hash = manifest_hash
        return True

    def reload(self) -> bool:
        """Force reload of artifacts."""
        return self.load(force=True)
