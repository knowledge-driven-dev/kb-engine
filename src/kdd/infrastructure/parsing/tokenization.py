"""Token counting and truncation.

Ported from ``kb_engine/utils/tokenization.py``.
Uses a simple character-based estimation (no tiktoken dependency).
"""

from __future__ import annotations

# Average ~4 characters per token for English text.
_CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    """Return an approximate token count for *text*."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate *text* so it fits within *max_tokens* (approx)."""
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
