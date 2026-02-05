"""Custom exceptions for KB-Engine."""


class KBPodError(Exception):
    """Base exception for all KB-Engine errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(KBPodError):
    """Raised when there's a configuration problem."""

    pass


class ValidationError(KBPodError):
    """Raised when validation fails."""

    pass


class RepositoryError(KBPodError):
    """Raised when a repository operation fails."""

    pass


class ChunkingError(KBPodError):
    """Raised when chunking fails."""

    pass


class ExtractionError(KBPodError):
    """Raised when entity extraction fails."""

    pass


class EmbeddingError(KBPodError):
    """Raised when embedding generation fails."""

    pass


class PipelineError(KBPodError):
    """Raised when a pipeline step fails."""

    pass


class DocumentNotFoundError(KBPodError):
    """Raised when a document is not found."""

    pass


class DuplicateDocumentError(KBPodError):
    """Raised when attempting to create a duplicate document."""

    pass
