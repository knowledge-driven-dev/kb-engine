"""Tokenization utilities."""

import tiktoken


def get_encoding(model: str = "gpt-4") -> tiktoken.Encoding:
    """Get the tokenizer encoding for a model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in text."""
    encoding = get_encoding(model)
    return len(encoding.encode(text))


def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-4") -> str:
    """Truncate text to a maximum number of tokens."""
    encoding = get_encoding(model)
    tokens = encoding.encode(text)

    if len(tokens) <= max_tokens:
        return text

    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)
