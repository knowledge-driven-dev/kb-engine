"""Hashing utilities."""

import hashlib


def compute_content_hash(content: str) -> str:
    """Compute a SHA-256 hash of content.

    Used for detecting document changes and deduplication.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
