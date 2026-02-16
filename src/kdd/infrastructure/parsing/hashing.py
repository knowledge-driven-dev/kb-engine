"""Hashing utilities.

Ported from ``kb_engine/utils/hashing.py``.
"""

from __future__ import annotations

import hashlib


def compute_content_hash(content: str) -> str:
    """Compute a SHA-256 hex digest of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
