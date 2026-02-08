"""Entity document schema definition."""

from kb_engine.smart.types import (
    ChunkingStrategy,
    ContentExpectation,
    FieldDefinition,
    KDDDocumentKind,
    SectionDefinition,
    TemplateSchema,
)

# Column names for table parsing (ES/EN)
ATTRIBUTES_TABLE_COLUMNS = ["Atributo", "Code", "Tipo", "Descripción"]
ATTRIBUTES_TABLE_COLUMNS_EN = ["Attribute", "Code", "Type", "Description"]

RELATIONS_TABLE_COLUMNS = ["Relación", "Code", "Cardinalidad", "Entidad", "Descripción"]
RELATIONS_TABLE_COLUMNS_EN = ["Relation", "Code", "Cardinality", "Entity", "Description"]

STATES_TABLE_COLUMNS = ["Estado", "Descripción", "Condiciones de entrada"]
STATES_TABLE_COLUMNS_EN = ["State", "Description", "Entry Conditions"]


ENTITY_SCHEMA = TemplateSchema(
    kind=KDDDocumentKind.ENTITY,
    title_is_name=True,
    frontmatter_fields=[
        FieldDefinition(name="kind", required=True, field_type="string"),
        FieldDefinition(name="aliases", required=False, field_type="array"),
        FieldDefinition(name="code", required=False, field_type="object"),
        FieldDefinition(name="tags", required=True, field_type="array"),
    ],
    required_sections=[
        SectionDefinition(
            name="Descripción",
            aliases=["Description"],
            required=True,
            content_expectation=ContentExpectation.TEXT,
            chunking_strategy=ChunkingStrategy.KEEP_INTACT,
            description="Entity description",
        ),
        SectionDefinition(
            name="Atributos",
            aliases=["Attributes"],
            required=True,
            content_expectation=ContentExpectation.TABLE,
            chunking_strategy=ChunkingStrategy.TABLE_ROWS,
            description="Entity attributes table",
        ),
    ],
    optional_sections=[
        SectionDefinition(
            name="Relaciones",
            aliases=["Relations", "Relationships"],
            content_expectation=ContentExpectation.TABLE,
            chunking_strategy=ChunkingStrategy.TABLE_ROWS,
            description="Entity relationships table",
        ),
        SectionDefinition(
            name="Ciclo de Vida",
            aliases=["Lifecycle", "Life Cycle"],
            content_expectation=ContentExpectation.MERMAID_STATE,
            chunking_strategy=ChunkingStrategy.KEEP_INTACT,
            description="State diagram",
        ),
        SectionDefinition(
            name="Estados",
            aliases=["States"],
            content_expectation=ContentExpectation.TABLE,
            chunking_strategy=ChunkingStrategy.TABLE_ROWS,
            description="States table",
        ),
        SectionDefinition(
            name="Invariantes",
            aliases=["Invariants", "Constraints"],
            content_expectation=ContentExpectation.TEXT,
            chunking_strategy=ChunkingStrategy.SPLIT_BY_ITEMS,
            description="Business rules",
        ),
        SectionDefinition(
            name="Eventos",
            aliases=["Events"],
            content_expectation=ContentExpectation.TEXT,
            chunking_strategy=ChunkingStrategy.KEEP_INTACT,
            description="Events emitted/consumed",
        ),
    ],
)
