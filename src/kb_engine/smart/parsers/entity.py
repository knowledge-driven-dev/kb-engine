"""Parser for Entity KDD documents."""

import re
from typing import Any

import frontmatter
import structlog

from kb_engine.smart.schemas.entity import (
    ATTRIBUTES_TABLE_COLUMNS,
    ATTRIBUTES_TABLE_COLUMNS_EN,
    ENTITY_SCHEMA,
    RELATIONS_TABLE_COLUMNS,
    RELATIONS_TABLE_COLUMNS_EN,
    STATES_TABLE_COLUMNS,
    STATES_TABLE_COLUMNS_EN,
)
from kb_engine.smart.types import (
    ContentExpectation,
    ExtractedAttribute,
    ExtractedEntityInfo,
    ExtractedRelation,
    ExtractedState,
    KDDDocumentKind,
    ParsedCodeBlock,
    ParsedDocument,
    ParsedSection,
    ParsedTable,
    TemplateSchema,
)

logger = structlog.get_logger(__name__)


class EntityParser:
    """Parser for Entity KDD documents."""

    def __init__(self, schema: TemplateSchema | None = None) -> None:
        """Initialize parser with schema."""
        self.schema = schema or ENTITY_SCHEMA

    def parse(self, content: str, filename: str | None = None) -> ParsedDocument:
        """Parse an entity document."""
        log = logger.bind(filename=filename)
        log.debug("parser.entity.start", content_length=len(content))

        fm = frontmatter.loads(content)
        body = fm.content
        log.debug("parser.entity.frontmatter", keys=list(fm.metadata.keys()))

        title = self._extract_title(body)
        log.debug("parser.entity.title", title=title)

        sections = self._parse_sections(body)
        log.debug("parser.entity.sections", count=len(sections), names=[s.name for s in sections])

        tables = self._extract_all_tables(body, sections)
        log.debug("parser.entity.tables", count=len(tables))

        # Associate tables with sections
        for table in tables:
            for section in sections:
                if section.name == table.section_name:
                    section.tables.append(table)

        code_blocks = self._extract_code_blocks(body, sections)
        log.debug("parser.entity.code_blocks", count=len(code_blocks))

        # Associate code blocks with sections
        for block in code_blocks:
            for section in sections:
                if section.name == block.section_name:
                    section.code_blocks.append(block)

        cross_refs = self._extract_cross_references(body)
        log.debug("parser.entity.cross_refs", count=len(cross_refs))

        parsed = ParsedDocument(
            kind=KDDDocumentKind.ENTITY,
            frontmatter=dict(fm.metadata),
            title=title,
            sections=sections,
            tables=tables,
            code_blocks=code_blocks,
            cross_references=cross_refs,
            validation_errors=[],
            raw_content=content,
        )

        parsed.validation_errors = self._validate(parsed)
        if parsed.validation_errors:
            log.warning("parser.entity.validation_errors", errors=parsed.validation_errors)

        log.debug("parser.entity.complete", title=title)
        return parsed

    def extract_entity_info(self, parsed: ParsedDocument) -> ExtractedEntityInfo:
        """Extract structured entity information from parsed document."""
        log = logger.bind(entity_name=parsed.entity_name)
        log.debug("parser.extract_info.start")

        description = ""
        for section in parsed.sections:
            if section.name.lower() in ["descripción", "description"]:
                description = section.content
                break

        attributes = self._extract_attributes(parsed)
        log.debug("parser.extract_info.attributes", count=len(attributes))

        relations = self._extract_relations(parsed)
        log.debug("parser.extract_info.relations", count=len(relations))

        states = self._extract_states(parsed)
        log.debug("parser.extract_info.states", count=len(states))

        invariants = self._extract_invariants(parsed)
        log.debug("parser.extract_info.invariants", count=len(invariants))

        events_emitted, events_consumed = self._extract_events(parsed)
        log.debug("parser.extract_info.events", emitted=len(events_emitted), consumed=len(events_consumed))

        return ExtractedEntityInfo(
            name=parsed.entity_name,
            aliases=parsed.aliases,
            code_class=parsed.code_class,
            code_table=parsed.code_table,
            description=description,
            attributes=attributes,
            relations=relations,
            states=states,
            invariants=invariants,
            events_emitted=events_emitted,
            events_consumed=events_consumed,
            cross_references=parsed.cross_references,
        )

    def _extract_title(self, body: str) -> str:
        """Extract title from first H1 heading."""
        match = re.search(r"^#\s+(.+?)(?:\s*<!--.*-->)?$", body, re.MULTILINE)
        return match.group(1).strip() if match else "Untitled"

    def _parse_sections(self, body: str) -> list[ParsedSection]:
        """Parse all sections from document body."""
        sections: list[ParsedSection] = []
        current_section: ParsedSection | None = None
        current_content: list[str] = []
        offset = 0

        lines = body.split("\n")

        for line in lines:
            line_length = len(line) + 1

            # Check for heading
            heading_match = re.match(r"^(#{2,6})\s+(.+?)(?:\s*<!--.*-->)?$", line)

            if heading_match:
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    current_section.end_offset = offset
                    sections.append(current_section)

                level = len(heading_match.group(1))
                name = heading_match.group(2).strip()

                current_section = ParsedSection(
                    name=name,
                    level=level,
                    content="",
                    start_offset=offset,
                )
                current_content = []
            elif current_section:
                current_content.append(line)

            offset += line_length

        # Don't forget the last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            current_section.end_offset = offset
            sections.append(current_section)

        return sections

    def _extract_all_tables(self, body: str, sections: list[ParsedSection]) -> list[ParsedTable]:
        """Extract all markdown tables from body."""
        tables: list[ParsedTable] = []
        table_pattern = re.compile(
            r"^\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)+)",
            re.MULTILINE,
        )

        for match in table_pattern.finditer(body):
            header_line = match.group(1)
            rows_text = match.group(2)

            headers = [h.strip().strip("`") for h in header_line.split("|") if h.strip()]
            rows = []

            for row_line in rows_text.strip().split("\n"):
                cells = [c.strip() for c in row_line.split("|") if c.strip() or row_line.count("|") > len(headers)]
                # Filter empty leading/trailing cells from split
                cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
                if cells:
                    rows.append(cells)

            # Find which section this table belongs to
            table_pos = match.start()
            section_name = "Unknown"
            for section in sections:
                if section.start_offset <= table_pos < section.end_offset:
                    section_name = section.name
                    break

            tables.append(ParsedTable(
                headers=headers,
                rows=rows,
                section_name=section_name,
                raw_content=match.group(0),
            ))

        return tables

    def _extract_code_blocks(self, body: str, sections: list[ParsedSection]) -> list[ParsedCodeBlock]:
        """Extract code blocks from body."""
        blocks: list[ParsedCodeBlock] = []
        pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

        for match in pattern.finditer(body):
            language = match.group(1) or "text"
            content = match.group(2)

            # Find section
            block_pos = match.start()
            section_name = "Unknown"
            for section in sections:
                if section.start_offset <= block_pos < section.end_offset:
                    section_name = section.name
                    break

            blocks.append(ParsedCodeBlock(
                language=language,
                content=content,
                section_name=section_name,
            ))

        return blocks

    def _extract_cross_references(self, body: str) -> list[str]:
        """Extract [[Reference]] links from body."""
        pattern = re.compile(r"\[\[([^\]]+)\]\]")
        refs = pattern.findall(body)
        return list(set(refs))

    def _validate(self, parsed: ParsedDocument) -> list[str]:
        """Validate parsed document against schema."""
        errors = []

        # Check required sections
        section_names = {s.name.lower() for s in parsed.sections}
        for req in self.schema.required_sections:
            names_to_check = {req.name.lower()} | {a.lower() for a in req.aliases}
            if not names_to_check & section_names:
                errors.append(f"Missing required section: {req.name}")

        return errors

    def _extract_attributes(self, parsed: ParsedDocument) -> list[ExtractedAttribute]:
        """Extract attributes from Atributos table."""
        attributes = []

        for table in parsed.tables:
            if table.section_name.lower() not in ["atributos", "attributes"]:
                continue

            headers_lower = [h.lower() for h in table.headers]

            for row in table.rows:
                if len(row) < 2:
                    continue

                # Find column indices
                name_idx = 0
                code_idx = self._find_column(headers_lower, ["code"])
                type_idx = self._find_column(headers_lower, ["tipo", "type"])
                desc_idx = self._find_column(headers_lower, ["descripción", "description"])

                name = row[name_idx].strip("`") if name_idx < len(row) else ""
                code = row[code_idx].strip("`") if code_idx is not None and code_idx < len(row) else None
                attr_type = row[type_idx] if type_idx is not None and type_idx < len(row) else "unknown"
                description = row[desc_idx] if desc_idx is not None and desc_idx < len(row) else ""

                # Check if reference type (contains [[Entity]])
                is_reference = "[[" in attr_type
                reference_entity = None
                if is_reference:
                    ref_match = re.search(r"\[\[(\w+)\]\]", attr_type)
                    if ref_match:
                        reference_entity = ref_match.group(1)

                attributes.append(ExtractedAttribute(
                    name=name,
                    code=code,
                    type=attr_type,
                    description=description,
                    is_reference=is_reference,
                    reference_entity=reference_entity,
                ))

        return attributes

    def _extract_relations(self, parsed: ParsedDocument) -> list[ExtractedRelation]:
        """Extract relations from Relaciones table."""
        relations = []

        for table in parsed.tables:
            if table.section_name.lower() not in ["relaciones", "relations", "relationships"]:
                continue

            headers_lower = [h.lower() for h in table.headers]

            for row in table.rows:
                if len(row) < 3:
                    continue

                name_idx = 0
                code_idx = self._find_column(headers_lower, ["code"])
                card_idx = self._find_column(headers_lower, ["cardinalidad", "cardinality"])
                entity_idx = self._find_column(headers_lower, ["entidad", "entity"])
                desc_idx = self._find_column(headers_lower, ["descripción", "description"])

                name = row[name_idx].strip("`") if name_idx < len(row) else ""
                code = row[code_idx].strip("`") if code_idx is not None and code_idx < len(row) else None
                cardinality = row[card_idx] if card_idx is not None and card_idx < len(row) else ""
                target_raw = row[entity_idx] if entity_idx is not None and entity_idx < len(row) else ""
                description = row[desc_idx] if desc_idx is not None and desc_idx < len(row) else ""

                # Extract entity name from [[Entity]]
                target_match = re.search(r"\[\[(\w+)\]\]", target_raw)
                target_entity = target_match.group(1) if target_match else target_raw

                relations.append(ExtractedRelation(
                    name=name,
                    code=code,
                    cardinality=cardinality,
                    target_entity=target_entity,
                    description=description,
                ))

        return relations

    def _extract_states(self, parsed: ParsedDocument) -> list[ExtractedState]:
        """Extract states from Estados table."""
        states = []

        for table in parsed.tables:
            if table.section_name.lower() not in ["estados", "states"]:
                continue

            headers_lower = [h.lower() for h in table.headers]

            for row in table.rows:
                if len(row) < 2:
                    continue

                name_idx = 0
                desc_idx = self._find_column(headers_lower, ["descripción", "description"])
                cond_idx = self._find_column(headers_lower, ["condiciones de entrada", "entry conditions"])

                name = row[name_idx].strip("*").strip()
                description = row[desc_idx] if desc_idx is not None and desc_idx < len(row) else ""
                entry_conditions = row[cond_idx] if cond_idx is not None and cond_idx < len(row) else ""

                states.append(ExtractedState(
                    name=name,
                    description=description,
                    entry_conditions=entry_conditions,
                ))

        return states

    def _extract_invariants(self, parsed: ParsedDocument) -> list[str]:
        """Extract invariants from Invariantes section."""
        invariants = []

        for section in parsed.sections:
            if section.name.lower() not in ["invariantes", "invariants", "constraints"]:
                continue

            # Extract list items
            for line in section.content.split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    invariants.append(line[2:].strip())

        return invariants

    def _extract_events(self, parsed: ParsedDocument) -> tuple[list[str], list[str]]:
        """Extract events emitted and consumed."""
        emitted = []
        consumed = []

        for section in parsed.sections:
            if section.name.lower() not in ["eventos", "events"]:
                continue

            for line in section.content.split("\n"):
                line_lower = line.lower()

                if "emite" in line_lower or "emit" in line_lower or "produce" in line_lower:
                    refs = re.findall(r"\[\[([^\]]+)\]\]", line)
                    emitted.extend(refs)
                elif "consume" in line_lower or "escucha" in line_lower or "listen" in line_lower:
                    refs = re.findall(r"\[\[([^\]]+)\]\]", line)
                    consumed.extend(refs)

        return list(set(emitted)), list(set(consumed))

    def _find_column(self, headers: list[str], names: list[str]) -> int | None:
        """Find column index by possible names."""
        for name in names:
            if name in headers:
                return headers.index(name)
        return None
