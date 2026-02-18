"""Core types for the smart ingestion pipeline."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class KDDDocumentKind(str, Enum):
    """KDD document types."""

    ENTITY = "entity"
    USE_CASE = "use-case"
    RULE = "rule"
    PROCESS = "process"
    EVENT = "event"
    COMMAND = "command"
    QUERY = "query"
    ADR = "adr"
    PRD = "prd"
    NFR = "nfr"
    STORY = "story"
    UI_VIEW = "ui-view"
    UI_FLOW = "ui-flow"
    UI_COMPONENT = "ui-component"
    IDEA = "idea"
    REQUIREMENT = "requirement"
    IMPLEMENTATION_CHARTER = "implementation-charter"
    UNKNOWN = "unknown"


class ChunkingStrategy(str, Enum):
    """Chunking strategies for different content types."""

    DEFAULT = "default"
    KEEP_INTACT = "keep_intact"
    TABLE_ROWS = "table_rows"
    SPLIT_BY_ITEMS = "split_by_items"
    SPLIT_BY_PARAGRAPHS = "split_by_paragraphs"


class ContentExpectation(str, Enum):
    """Expected content types for sections."""

    TEXT = "text"
    TABLE = "table"
    MERMAID_STATE = "mermaid:stateDiagram-v2"
    MERMAID_FLOW = "mermaid:flowchart"
    YAML = "yaml"
    JSON = "json"
    CODE = "code"


@dataclass
class DetectionResult:
    """Result of document kind detection."""

    kind: KDDDocumentKind
    confidence: float
    detected_from: str  # "frontmatter", "filename", "content"


@dataclass
class FieldDefinition:
    """Definition of a frontmatter field."""

    name: str
    required: bool = False
    field_type: str = "string"
    description: str = ""


@dataclass
class SectionDefinition:
    """Definition of a document section."""

    name: str
    required: bool = False
    aliases: list[str] = field(default_factory=list)
    content_expectation: ContentExpectation = ContentExpectation.TEXT
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.DEFAULT
    description: str = ""


@dataclass
class TemplateSchema:
    """Schema for a KDD document template."""

    kind: KDDDocumentKind
    title_is_name: bool = False
    frontmatter_fields: list[FieldDefinition] = field(default_factory=list)
    required_sections: list[SectionDefinition] = field(default_factory=list)
    optional_sections: list[SectionDefinition] = field(default_factory=list)


@dataclass
class ParsedTable:
    """A parsed markdown table."""

    headers: list[str]
    rows: list[list[str]]
    section_name: str
    raw_content: str


@dataclass
class ParsedCodeBlock:
    """A parsed code block."""

    language: str
    content: str
    section_name: str


@dataclass
class ParsedSection:
    """A parsed document section."""

    name: str
    level: int
    content: str
    content_type: ContentExpectation = ContentExpectation.TEXT
    tables: list[ParsedTable] = field(default_factory=list)
    code_blocks: list[ParsedCodeBlock] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0


@dataclass
class ParsedDocument:
    """A fully parsed KDD document."""

    kind: KDDDocumentKind
    frontmatter: dict[str, Any]
    title: str
    sections: list[ParsedSection]
    tables: list[ParsedTable]
    code_blocks: list[ParsedCodeBlock]
    cross_references: list[str]
    validation_errors: list[str]
    raw_content: str

    @property
    def entity_name(self) -> str:
        """Get entity name (title for entity documents)."""
        return self.title

    @property
    def aliases(self) -> list[str]:
        """Get aliases from frontmatter."""
        return self.frontmatter.get("aliases", [])

    @property
    def code_class(self) -> str | None:
        """Get code class name."""
        code = self.frontmatter.get("code", {})
        return code.get("class") if isinstance(code, dict) else None

    @property
    def code_table(self) -> str | None:
        """Get code table name."""
        code = self.frontmatter.get("code", {})
        return code.get("table") if isinstance(code, dict) else None


@dataclass
class HierarchicalContext:
    """Context for hierarchical chunking."""

    document_summary: str
    section_summaries: list[str]
    heading_path: list[str]

    def as_prefix(self) -> str:
        """Generate context prefix for chunk."""
        parts = []
        if self.document_summary:
            parts.append(f"[Doc: {self.document_summary}]")
        if self.section_summaries:
            parts.append(f"[Sec: {self.section_summaries[-1]}]")
        return " > ".join(parts)


@dataclass
class ContextualizedChunk:
    """A chunk with hierarchical context."""

    id: str
    content: str
    contextualized_content: str
    chunk_type: str
    context: HierarchicalContext
    document_id: str
    document_kind: KDDDocumentKind
    section_name: str
    sequence: int
    table_headers: list[str] | None = None
    row_index: int | None = None
    row_data: dict[str, str] | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass
class ExtractedAttribute:
    """An extracted entity attribute."""

    name: str
    code: str | None
    type: str
    description: str
    is_reference: bool = False
    reference_entity: str | None = None


@dataclass
class ExtractedRelation:
    """An extracted entity relation."""

    name: str
    code: str | None
    cardinality: str
    target_entity: str
    description: str


@dataclass
class ExtractedState:
    """An extracted entity state."""

    name: str
    description: str
    is_initial: bool = False
    is_final: bool = False
    entry_conditions: str = ""


@dataclass
class ExtractedEntityInfo:
    """All extracted info from an entity document."""

    name: str
    aliases: list[str]
    code_class: str | None
    code_table: str | None
    description: str
    attributes: list[ExtractedAttribute]
    relations: list[ExtractedRelation]
    states: list[ExtractedState]
    invariants: list[str]
    events_emitted: list[str]
    events_consumed: list[str]
    cross_references: list[str]


@dataclass
class IngestionResult:
    """Result of document ingestion."""

    success: bool = False
    document_id: str = ""
    document_kind: KDDDocumentKind = KDDDocumentKind.UNKNOWN
    detection_confidence: float = 0.0
    chunks_created: int = 0
    entities_extracted: int = 0
    relations_created: int = 0
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
