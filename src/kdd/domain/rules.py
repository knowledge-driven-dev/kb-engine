"""Business rules as pure functions.

Each function implements a spec from ``specs/01-domain/rules/`` and is
fully deterministic — no I/O, no side-effects, easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer


# ---------------------------------------------------------------------------
# BR-DOCUMENT-001 — Kind Router
# ---------------------------------------------------------------------------

# Front-matter ``kind`` string → KDDKind enum
KIND_LOOKUP: dict[str, KDDKind] = {k.value: k for k in KDDKind}

# kind → expected folder prefix (for location warnings)
KIND_EXPECTED_PATH: dict[KDDKind, str] = {
    KDDKind.ENTITY: "01-domain/entities/",
    KDDKind.EVENT: "01-domain/events/",
    KDDKind.BUSINESS_RULE: "01-domain/rules/",
    KDDKind.BUSINESS_POLICY: "02-behavior/policies/",
    KDDKind.CROSS_POLICY: "02-behavior/policies/",
    KDDKind.COMMAND: "02-behavior/commands/",
    KDDKind.QUERY: "02-behavior/queries/",
    KDDKind.PROCESS: "02-behavior/processes/",
    KDDKind.USE_CASE: "02-behavior/use-cases/",
    KDDKind.UI_VIEW: "03-experience/views/",
    KDDKind.UI_COMPONENT: "03-experience/views/",
    KDDKind.REQUIREMENT: "04-verification/criteria/",
    KDDKind.OBJECTIVE: "00-requirements/objectives/",
    KDDKind.PRD: "00-requirements/",
    KDDKind.ADR: "00-requirements/decisions/",
}


@dataclass
class RouteResult:
    """Result of routing a document to its kind."""

    kind: KDDKind | None
    warning: str | None = None


def route_document(
    front_matter: dict[str, Any] | None,
    source_path: str,
) -> RouteResult:
    """Determine the KDDKind and validate location (BR-DOCUMENT-001).

    Returns ``RouteResult(kind=None)`` when the document should be ignored
    (no front-matter or unrecognised kind).
    """
    if not front_matter:
        return RouteResult(kind=None)

    kind_str = str(front_matter.get("kind", "")).lower().strip()
    if not kind_str or kind_str not in KIND_LOOKUP:
        return RouteResult(kind=None)

    kind = KIND_LOOKUP[kind_str]

    # Check expected location
    expected = KIND_EXPECTED_PATH.get(kind, "")
    warning = None
    if expected and expected not in source_path:
        warning = (
            f"{kind.value} '{source_path}' found outside "
            f"expected path '{expected}'"
        )

    return RouteResult(kind=kind, warning=warning)


# ---------------------------------------------------------------------------
# BR-EMBEDDING-001 — Embedding Strategy
# ---------------------------------------------------------------------------

# kind → set of embeddable section headings (normalised to lowercase).
# An empty set means the kind produces no embeddings at all.
EMBEDDABLE_SECTIONS: dict[KDDKind, set[str]] = {
    KDDKind.ENTITY: {"descripción", "description"},
    KDDKind.EVENT: set(),  # no embeddings
    KDDKind.BUSINESS_RULE: {"declaración", "declaration", "cuándo aplica", "when applies"},
    KDDKind.BUSINESS_POLICY: {"declaración", "declaration"},
    KDDKind.CROSS_POLICY: {"propósito", "purpose", "declaración", "declaration"},
    KDDKind.COMMAND: {"purpose", "propósito"},
    KDDKind.QUERY: {"purpose", "propósito"},
    KDDKind.PROCESS: {"participantes", "participants", "pasos", "steps"},
    KDDKind.USE_CASE: {"descripción", "description", "flujo principal", "main flow"},
    KDDKind.UI_VIEW: {"descripción", "description", "comportamiento", "behavior"},
    KDDKind.UI_COMPONENT: {"descripción", "description"},
    KDDKind.REQUIREMENT: {"descripción", "description"},
    KDDKind.OBJECTIVE: {"objetivo", "objective"},
    KDDKind.PRD: {"problema / oportunidad", "problem / opportunity"},
    KDDKind.ADR: {"contexto", "context", "decisión", "decision"},
}


def embeddable_sections(kind: KDDKind) -> set[str]:
    """Return the set of embeddable section headings for a kind (BR-EMBEDDING-001)."""
    return EMBEDDABLE_SECTIONS.get(kind, set())


# ---------------------------------------------------------------------------
# BR-INDEX-001 — Index Level detection
# ---------------------------------------------------------------------------


def detect_index_level(
    *,
    embedding_model_available: bool,
    agent_api_available: bool,
) -> IndexLevel:
    """Determine the highest indexing level available (BR-INDEX-001)."""
    if agent_api_available and embedding_model_available:
        return IndexLevel.L3
    if embedding_model_available:
        return IndexLevel.L2
    return IndexLevel.L1


# ---------------------------------------------------------------------------
# BR-LAYER-001 — Layer Validation
# ---------------------------------------------------------------------------

# Layer prefix → KDDLayer
LAYER_BY_PREFIX: dict[str, KDDLayer] = {
    "00-requirements": KDDLayer.REQUIREMENTS,
    "01-domain": KDDLayer.DOMAIN,
    "02-behavior": KDDLayer.BEHAVIOR,
    "03-experience": KDDLayer.EXPERIENCE,
    "04-verification": KDDLayer.VERIFICATION,
}


def detect_layer(source_path: str) -> KDDLayer | None:
    """Infer the KDD layer from a file's path prefix."""
    for prefix, layer in LAYER_BY_PREFIX.items():
        if prefix in source_path:
            return layer
    return None


def is_layer_violation(
    origin_layer: KDDLayer,
    destination_layer: KDDLayer,
) -> bool:
    """Return True if an edge from origin to destination violates layer deps.

    Rules (BR-LAYER-001):
    - ``00-requirements`` is exempt — never a violation when it's the origin.
    - A violation occurs when the origin's numeric layer is > 0 and is
      strictly lower than the destination's numeric layer
      (i.e. a lower layer references a higher layer).
    """
    if origin_layer == KDDLayer.REQUIREMENTS:
        return False
    return origin_layer.numeric < destination_layer.numeric


# ---------------------------------------------------------------------------
# BR-MERGE-001 — Merge Conflict Resolution
# ---------------------------------------------------------------------------

@dataclass
class ConflictResult:
    """Outcome of a node conflict resolution."""

    winner_index: int  # index into the list of candidates
    reason: str


def resolve_node_conflict(
    candidates: list[dict[str, Any]],
) -> ConflictResult:
    """Resolve a node conflict using last-write-wins (BR-MERGE-001).

    Each candidate dict must contain ``indexed_at`` (ISO datetime string
    or datetime object) and ``source_hash``.

    If all hashes are identical the first candidate wins (equivalent copies).
    """
    if len(candidates) == 1:
        return ConflictResult(winner_index=0, reason="single")

    # Identical hashes → take first
    hashes = {c["source_hash"] for c in candidates}
    if len(hashes) == 1:
        return ConflictResult(winner_index=0, reason="identical")

    # Last-write-wins by indexed_at
    best_idx = 0
    best_ts = candidates[0]["indexed_at"]
    for i, c in enumerate(candidates[1:], start=1):
        if c["indexed_at"] > best_ts:
            best_ts = c["indexed_at"]
            best_idx = i

    return ConflictResult(winner_index=best_idx, reason="last-write-wins")


def resolve_deletion(
    present_in: list[bool],
    modified_after_deletion: bool = False,
) -> tuple[bool, str | None]:
    """Decide whether a node should be deleted during merge (BR-MERGE-001).

    ``present_in`` is a list of booleans, one per source index, indicating
    whether the node is present in that index.

    Returns ``(should_delete, warning)``.
    - Delete-wins: if the node is absent from *any* index, it's deleted.
    - If it was modified in another index after the deletion, a warning is
      returned.
    """
    if all(present_in):
        return False, None

    warning = None
    if modified_after_deletion:
        warning = "Node was modified in another index after deletion"

    return True, warning
