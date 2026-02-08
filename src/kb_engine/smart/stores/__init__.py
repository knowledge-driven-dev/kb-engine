"""Storage backends for the smart pipeline."""

from kb_engine.smart.stores.falkordb_graph import FalkorDBGraphStore

# Alias for backwards compatibility (deprecated - use FalkorDBGraphStore)
KuzuGraphStore = FalkorDBGraphStore

__all__ = [
    "FalkorDBGraphStore",
    "KuzuGraphStore",  # deprecated alias
]
