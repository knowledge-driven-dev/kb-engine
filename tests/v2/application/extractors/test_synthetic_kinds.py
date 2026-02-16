"""Tests for extractors that don't yet have real spec files.

Uses synthetic markdown content to verify extractor behavior for:
business-policy, cross-policy, process, ui-view, ui-component,
objective, adr.
"""

from kdd.application.extractors.kinds.adr import ADRExtractor
from kdd.application.extractors.kinds.business_policy import PolicyExtractor
from kdd.application.extractors.kinds.cross_policy import CrossPolicyExtractor
from kdd.application.extractors.kinds.objective import ObjectiveExtractor
from kdd.application.extractors.kinds.process import ProcessExtractor
from kdd.application.extractors.kinds.ui_component import UIComponentExtractor
from kdd.application.extractors.kinds.ui_view import UIViewExtractor
from kdd.domain.enums import KDDKind

from .conftest import build_synthetic_document


# ---------------------------------------------------------------------------
# Business Policy
# ---------------------------------------------------------------------------

_BP_CONTENT = """\
---
id: BP-NAMING-001
kind: business-policy
status: draft
---

# BP-NAMING-001 — Naming Policy

## Declaración

Todos los nombres de [[KDDDocument]] deben seguir el patrón PascalCase.

## Cuándo Aplica

Cuando se crea un nuevo documento KDD.

## Parámetros

Ninguno configurable.

## Qué pasa si se incumple

El pipeline de indexación emite un warning y continúa.
"""


class TestPolicyExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _BP_CONTENT,
            spec_path="specs/02-behavior/policies/BP-NAMING-001.md",
        )
        self.extractor = PolicyExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.BUSINESS_POLICY

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "BP:BP-NAMING-001"

    def test_node_has_declaration(self):
        node = self.extractor.extract_node(self.doc)
        assert "declaration" in node.indexed_fields
        assert "PascalCase" in node.indexed_fields["declaration"]

    def test_node_has_when_applies(self):
        node = self.extractor.extract_node(self.doc)
        assert "when_applies" in node.indexed_fields

    def test_node_has_violation(self):
        node = self.extractor.extract_node(self.doc)
        assert "violation" in node.indexed_fields

    def test_edges_include_entity_rule(self):
        edges = self.extractor.extract_edges(self.doc)
        entity_rules = [e for e in edges if e.edge_type == "ENTITY_RULE"]
        assert len(entity_rules) >= 1
        assert any("KDDDocument" in e.to_node for e in entity_rules)

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "BP:BP-NAMING-001"


# ---------------------------------------------------------------------------
# Cross Policy
# ---------------------------------------------------------------------------

_XP_CONTENT = """\
---
id: XP-AUDIT-001
kind: cross-policy
status: draft
---

# XP-AUDIT-001 — Audit Trail

## Propósito

Garantizar trazabilidad de todas las operaciones.

## Declaración

Toda operación sobre [[IndexManifest]] debe registrar un evento de auditoría.

## Formalización EARS

When a document is indexed, the system shall emit an audit event.

## Comportamiento Estándar

El sistema registra: timestamp, operación, usuario, resultado.
"""


class TestCrossPolicyExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _XP_CONTENT,
            spec_path="specs/02-behavior/policies/XP-AUDIT-001.md",
        )
        self.extractor = CrossPolicyExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.CROSS_POLICY

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "XP:XP-AUDIT-001"

    def test_node_has_purpose(self):
        node = self.extractor.extract_node(self.doc)
        assert "purpose" in node.indexed_fields

    def test_node_has_declaration(self):
        node = self.extractor.extract_node(self.doc)
        assert "declaration" in node.indexed_fields

    def test_node_has_formalization(self):
        node = self.extractor.extract_node(self.doc)
        assert "formalization_ears" in node.indexed_fields

    def test_node_has_standard_behavior(self):
        node = self.extractor.extract_node(self.doc)
        assert "standard_behavior" in node.indexed_fields

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "XP:XP-AUDIT-001"


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

_PROC_CONTENT = """\
---
id: PROC-001
kind: process
status: draft
---

# PROC-001 — Index Pipeline

## Participantes

- [[KDDDocument]] producer
- IndexPipeline orchestrator

## Pasos

### Paso 1: Detección

El sistema detecta cambios via git diff.

### Paso 2: Extracción

El extractor procesa el documento y genera [[GraphNode]].

## Diagrama

```mermaid
graph LR
    A[Detect] --> B[Extract] --> C[Store]
```
"""


class TestProcessExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _PROC_CONTENT,
            spec_path="specs/02-behavior/processes/PROC-001.md",
        )
        self.extractor = ProcessExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.PROCESS

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "PROC:PROC-001"

    def test_node_has_participants(self):
        node = self.extractor.extract_node(self.doc)
        assert "participants" in node.indexed_fields

    def test_node_has_steps(self):
        node = self.extractor.extract_node(self.doc)
        assert "steps" in node.indexed_fields
        # Steps should include sub-sections
        assert "Detección" in node.indexed_fields["steps"]

    def test_node_has_mermaid_flow(self):
        node = self.extractor.extract_node(self.doc)
        assert "mermaid_flow" in node.indexed_fields
        assert "mermaid" in node.indexed_fields["mermaid_flow"]

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "PROC:PROC-001"


# ---------------------------------------------------------------------------
# UI View
# ---------------------------------------------------------------------------

_UI_VIEW_CONTENT = """\
---
id: UI-Dashboard
kind: ui-view
status: draft
---

# UI-Dashboard

## Descripción

Vista principal del dashboard que muestra el estado del índice.

## Layout

Grid de 2 columnas con sidebar.

## Componentes

- StatsCard
- GraphViewer
- SearchBar

## Estados

- Loading
- Ready
- Error

## Comportamiento

Al cargar, la vista solicita datos del [[IndexManifest]].
"""


class TestUIViewExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _UI_VIEW_CONTENT,
            spec_path="specs/03-experience/views/UI-Dashboard.md",
        )
        self.extractor = UIViewExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.UI_VIEW

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "UIView:UI-Dashboard"

    def test_node_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields

    def test_node_has_layout(self):
        node = self.extractor.extract_node(self.doc)
        assert "layout" in node.indexed_fields

    def test_node_has_components(self):
        node = self.extractor.extract_node(self.doc)
        assert "components" in node.indexed_fields

    def test_node_has_behavior(self):
        node = self.extractor.extract_node(self.doc)
        assert "behavior" in node.indexed_fields

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "UIView:UI-Dashboard"


# ---------------------------------------------------------------------------
# UI Component
# ---------------------------------------------------------------------------

_UI_COMP_CONTENT = """\
---
id: UI-SearchBar
kind: ui-component
status: draft
---

# UI-SearchBar

## Descripción

Componente de barra de búsqueda con autocompletado.

## Entidades

Consume datos de [[GraphNode]] y [[Embedding]].

## Casos de Uso

Utilizado en [[UC-004-RetrieveContext]].
"""


class TestUIComponentExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _UI_COMP_CONTENT,
            spec_path="specs/03-experience/views/UI-SearchBar.md",
        )
        self.extractor = UIComponentExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.UI_COMPONENT

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "UIComp:UI-SearchBar"

    def test_node_has_description(self):
        node = self.extractor.extract_node(self.doc)
        assert "description" in node.indexed_fields

    def test_node_has_entities(self):
        node = self.extractor.extract_node(self.doc)
        assert "entities" in node.indexed_fields

    def test_node_has_use_cases(self):
        node = self.extractor.extract_node(self.doc)
        assert "use_cases" in node.indexed_fields

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "UIComp:UI-SearchBar"


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------

_OBJ_CONTENT = """\
---
id: OBJ-001
kind: objective
status: draft
---

# OBJ-001 — Agent Retrieval

## Actor

Agente de IA (Claude Code, Codex, Cursor).

## Objetivo

Obtener contexto preciso de specs KDD para ejecutar tareas de desarrollo
con alta precisión, referenciando [[KDDDocument]] y [[GraphNode]].

## Criterios de éxito

- Retrieval precision >= 90%
- Tiempo de respuesta P95 < 300ms
"""


class TestObjectiveExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _OBJ_CONTENT,
            spec_path="specs/00-requirements/objectives/OBJ-001.md",
        )
        self.extractor = ObjectiveExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.OBJECTIVE

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "OBJ:OBJ-001"

    def test_node_has_actor(self):
        node = self.extractor.extract_node(self.doc)
        assert "actor" in node.indexed_fields

    def test_node_has_objective(self):
        node = self.extractor.extract_node(self.doc)
        assert "objective" in node.indexed_fields

    def test_node_has_success_criteria(self):
        node = self.extractor.extract_node(self.doc)
        assert "success_criteria" in node.indexed_fields

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "OBJ:OBJ-001"


# ---------------------------------------------------------------------------
# ADR
# ---------------------------------------------------------------------------

_ADR_CONTENT = """\
---
id: ADR-0001
kind: adr
status: accepted
---

# ADR-0001 — Repository Pattern

## Contexto

El sistema necesita abstraer el almacenamiento para soportar
múltiples backends: SQLite, PostgreSQL, filesystem.

## Decisión

Adoptamos el Repository Pattern con interfaces definidas
como Protocols de Python, referenciando [[ArtifactStore]].

## Consecuencias

- Positivas: facilidad de testing, intercambio de backends.
- Negativas: capa de abstracción adicional, posible overhead.
"""


class TestADRExtractor:
    def setup_method(self):
        self.doc = build_synthetic_document(
            _ADR_CONTENT,
            spec_path="specs/00-requirements/decisions/ADR-0001.md",
        )
        self.extractor = ADRExtractor()

    def test_kind(self):
        assert self.extractor.kind == KDDKind.ADR

    def test_node_id(self):
        node = self.extractor.extract_node(self.doc)
        assert node.id == "ADR:ADR-0001"

    def test_node_has_context(self):
        node = self.extractor.extract_node(self.doc)
        assert "context" in node.indexed_fields
        assert "almacenamiento" in node.indexed_fields["context"]

    def test_node_has_decision(self):
        node = self.extractor.extract_node(self.doc)
        assert "decision" in node.indexed_fields
        assert "Repository Pattern" in node.indexed_fields["decision"]

    def test_node_has_consequences(self):
        node = self.extractor.extract_node(self.doc)
        assert "consequences" in node.indexed_fields

    def test_edges_include_wiki_links(self):
        edges = self.extractor.extract_edges(self.doc)
        edge_types = {e.edge_type for e in edges}
        assert "WIKI_LINK" in edge_types

    def test_edges_from_correct_node(self):
        edges = self.extractor.extract_edges(self.doc)
        for edge in edges:
            assert edge.from_node == "ADR:ADR-0001"
