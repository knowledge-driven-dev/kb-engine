"""Core interfaces (protocols) for KB-Engine."""

from kb_engine.core.interfaces.chunkers import ChunkingStrategy
from kb_engine.core.interfaces.extractors import EntityExtractor
from kb_engine.core.interfaces.repositories import (
    GraphRepository,
    TraceabilityRepository,
    VectorRepository,
)

__all__ = [
    "TraceabilityRepository",
    "VectorRepository",
    "GraphRepository",
    "ChunkingStrategy",
    "EntityExtractor",
]
