"""Domain enumerations for KDD.

Spec references:
- KDDKind: PRD-KBEngine (Nodos del grafo), BR-DOCUMENT-001
- KDDLayer: BR-LAYER-001
- EdgeType: GraphEdge entity spec (structural edge types)
- IndexLevel: BR-INDEX-001
- RetrievalStrategy: RetrievalQuery entity spec
"""

from __future__ import annotations

from enum import Enum


class KDDKind(str, Enum):
    """The 15 KDD artifact types recognized by the engine.

    Each value corresponds to the ``kind`` field in a spec's front-matter
    and maps to a dedicated extractor (BR-DOCUMENT-001).
    """

    ENTITY = "entity"
    EVENT = "event"
    BUSINESS_RULE = "business-rule"
    BUSINESS_POLICY = "business-policy"
    CROSS_POLICY = "cross-policy"
    COMMAND = "command"
    QUERY = "query"
    PROCESS = "process"
    USE_CASE = "use-case"
    UI_VIEW = "ui-view"
    UI_COMPONENT = "ui-component"
    REQUIREMENT = "requirement"
    OBJECTIVE = "objective"
    PRD = "prd"
    ADR = "adr"


class KDDLayer(str, Enum):
    """KDD layers ordered from bottom (requirements) to top (verification).

    The numeric prefix determines the dependency direction:
    higher layers may reference lower layers, not the reverse (BR-LAYER-001).
    ``00-requirements`` is exempt from this rule.
    """

    REQUIREMENTS = "00-requirements"
    DOMAIN = "01-domain"
    BEHAVIOR = "02-behavior"
    EXPERIENCE = "03-experience"
    VERIFICATION = "04-verification"

    @property
    def numeric(self) -> int:
        """Return the numeric prefix (0-4) for layer comparison."""
        return int(self.value[:2])


class DocumentStatus(str, Enum):
    """Lifecycle states of a KDDDocument in the indexing pipeline."""

    DETECTED = "detected"
    PARSING = "parsing"
    INDEXED = "indexed"
    STALE = "stale"
    DELETED = "deleted"


class QueryStatus(str, Enum):
    """Lifecycle states of a RetrievalQuery."""

    RECEIVED = "received"
    RESOLVING = "resolving"
    COMPLETED = "completed"
    FAILED = "failed"


class EdgeType(str, Enum):
    """Structural (SCREAMING_SNAKE_CASE) edge types extracted by the engine.

    Business-domain edges (snake_case) are free-form strings defined by spec
    authors and are NOT enumerated here.
    """

    WIKI_LINK = "WIKI_LINK"
    DOMAIN_RELATION = "DOMAIN_RELATION"
    ENTITY_RULE = "ENTITY_RULE"
    ENTITY_POLICY = "ENTITY_POLICY"
    EMITS = "EMITS"
    CONSUMES = "CONSUMES"
    UC_APPLIES_RULE = "UC_APPLIES_RULE"
    UC_EXECUTES_CMD = "UC_EXECUTES_CMD"
    UC_STORY = "UC_STORY"
    VIEW_TRIGGERS_UC = "VIEW_TRIGGERS_UC"
    VIEW_USES_COMPONENT = "VIEW_USES_COMPONENT"
    COMPONENT_USES_ENTITY = "COMPONENT_USES_ENTITY"
    REQ_TRACES_TO = "REQ_TRACES_TO"
    VALIDATES = "VALIDATES"
    DECIDES_FOR = "DECIDES_FOR"
    CROSS_DOMAIN_REF = "CROSS_DOMAIN_REF"


class IndexLevel(str, Enum):
    """Progressive indexing levels (BR-INDEX-001).

    L1 is always available.  L2 requires a local embedding model.
    L3 requires an AI agent API key.
    """

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class RetrievalStrategy(str, Enum):
    """Available retrieval strategies (RetrievalQuery spec)."""

    GRAPH = "graph"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    IMPACT = "impact"
