"""Document parsers for KDD documents."""

from kb_engine.smart.parsers.detector import DocumentKindDetector
from kb_engine.smart.parsers.entity import EntityParser

__all__ = [
    "DocumentKindDetector",
    "EntityParser",
]
