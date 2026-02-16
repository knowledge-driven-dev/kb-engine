"""Tests for kdd.domain.rules — pure function tests for all 5 BRs."""

import pytest

from kdd.domain.enums import IndexLevel, KDDKind, KDDLayer
from kdd.domain.rules import (
    EMBEDDABLE_SECTIONS,
    KIND_EXPECTED_PATH,
    detect_index_level,
    detect_layer,
    embeddable_sections,
    is_layer_violation,
    resolve_deletion,
    resolve_node_conflict,
    route_document,
)


# ---------------------------------------------------------------------------
# BR-DOCUMENT-001 — route_document()
# ---------------------------------------------------------------------------


class TestRouteDocument:
    """BR-DOCUMENT-001: Kind Router."""

    @pytest.mark.parametrize("kind_str,expected_kind", [
        ("entity", KDDKind.ENTITY),
        ("event", KDDKind.EVENT),
        ("business-rule", KDDKind.BUSINESS_RULE),
        ("business-policy", KDDKind.BUSINESS_POLICY),
        ("cross-policy", KDDKind.CROSS_POLICY),
        ("command", KDDKind.COMMAND),
        ("query", KDDKind.QUERY),
        ("process", KDDKind.PROCESS),
        ("use-case", KDDKind.USE_CASE),
        ("ui-view", KDDKind.UI_VIEW),
        ("ui-component", KDDKind.UI_COMPONENT),
        ("requirement", KDDKind.REQUIREMENT),
        ("objective", KDDKind.OBJECTIVE),
        ("prd", KDDKind.PRD),
        ("adr", KDDKind.ADR),
    ])
    def test_all_15_kinds(self, kind_str, expected_kind):
        result = route_document(
            front_matter={"kind": kind_str},
            source_path=f"specs/{KIND_EXPECTED_PATH[expected_kind]}SomeFile.md",
        )
        assert result.kind == expected_kind
        assert result.warning is None

    def test_no_front_matter(self):
        result = route_document(front_matter=None, source_path="specs/README.md")
        assert result.kind is None

    def test_empty_front_matter(self):
        result = route_document(front_matter={}, source_path="specs/README.md")
        assert result.kind is None

    def test_unrecognised_kind(self):
        result = route_document(
            front_matter={"kind": "unknown-type"},
            source_path="specs/01-domain/foo.md",
        )
        assert result.kind is None

    def test_missing_kind_field(self):
        result = route_document(
            front_matter={"title": "Something"},
            source_path="specs/01-domain/foo.md",
        )
        assert result.kind is None

    def test_wrong_location_emits_warning(self):
        result = route_document(
            front_matter={"kind": "entity"},
            source_path="specs/02-behavior/MiEntidad.md",
        )
        assert result.kind == KDDKind.ENTITY  # front-matter wins
        assert result.warning is not None
        assert "outside expected path" in result.warning

    def test_correct_location_no_warning(self):
        result = route_document(
            front_matter={"kind": "entity"},
            source_path="specs/01-domain/entities/Pedido.md",
        )
        assert result.kind == KDDKind.ENTITY
        assert result.warning is None

    def test_kind_case_insensitive(self):
        result = route_document(
            front_matter={"kind": "Entity"},
            source_path="specs/01-domain/entities/Pedido.md",
        )
        assert result.kind == KDDKind.ENTITY

    def test_kind_whitespace_stripped(self):
        result = route_document(
            front_matter={"kind": "  entity  "},
            source_path="specs/01-domain/entities/Pedido.md",
        )
        assert result.kind == KDDKind.ENTITY


# ---------------------------------------------------------------------------
# BR-EMBEDDING-001 — embeddable_sections()
# ---------------------------------------------------------------------------


class TestEmbeddableSections:
    """BR-EMBEDDING-001: Embedding Strategy."""

    def test_entity_embeds_description(self):
        sections = embeddable_sections(KDDKind.ENTITY)
        assert "descripción" in sections or "description" in sections

    def test_event_has_no_embeddings(self):
        sections = embeddable_sections(KDDKind.EVENT)
        assert len(sections) == 0

    def test_business_rule_embeds_declaration_and_when_applies(self):
        sections = embeddable_sections(KDDKind.BUSINESS_RULE)
        assert "declaración" in sections or "declaration" in sections
        assert "cuándo aplica" in sections or "when applies" in sections

    def test_use_case_embeds_description_and_main_flow(self):
        sections = embeddable_sections(KDDKind.USE_CASE)
        assert "descripción" in sections or "description" in sections
        assert "flujo principal" in sections or "main flow" in sections

    def test_all_15_kinds_have_entry(self):
        for kind in KDDKind:
            # Must not raise KeyError
            result = embeddable_sections(kind)
            assert isinstance(result, set)

    def test_command_embeds_purpose(self):
        sections = embeddable_sections(KDDKind.COMMAND)
        assert "purpose" in sections or "propósito" in sections

    def test_prd_embeds_problem(self):
        sections = embeddable_sections(KDDKind.PRD)
        assert "problema / oportunidad" in sections or "problem / opportunity" in sections

    def test_adr_embeds_context_and_decision(self):
        sections = embeddable_sections(KDDKind.ADR)
        assert "contexto" in sections or "context" in sections
        assert "decisión" in sections or "decision" in sections


# ---------------------------------------------------------------------------
# BR-INDEX-001 — detect_index_level()
# ---------------------------------------------------------------------------


class TestDetectIndexLevel:
    """BR-INDEX-001: Index Level."""

    def test_no_resources_returns_l1(self):
        assert detect_index_level(
            embedding_model_available=False,
            agent_api_available=False,
        ) == IndexLevel.L1

    def test_embedding_only_returns_l2(self):
        assert detect_index_level(
            embedding_model_available=True,
            agent_api_available=False,
        ) == IndexLevel.L2

    def test_both_returns_l3(self):
        assert detect_index_level(
            embedding_model_available=True,
            agent_api_available=True,
        ) == IndexLevel.L3

    def test_agent_without_embedding_returns_l1(self):
        # Agent API without embedding model cannot do L3
        assert detect_index_level(
            embedding_model_available=False,
            agent_api_available=True,
        ) == IndexLevel.L1


# ---------------------------------------------------------------------------
# BR-LAYER-001 — is_layer_violation()
# ---------------------------------------------------------------------------


class TestIsLayerViolation:
    """BR-LAYER-001: Layer Validation.

    Validates BDD: layer-validation.feature SCN-001..004
    """

    def test_upper_to_lower_is_valid(self):
        # SCN-001: 02-behavior → 01-domain
        assert is_layer_violation(KDDLayer.BEHAVIOR, KDDLayer.DOMAIN) is False

    def test_lower_to_upper_is_violation(self):
        # SCN-002: 01-domain → 02-behavior
        assert is_layer_violation(KDDLayer.DOMAIN, KDDLayer.BEHAVIOR) is True

    def test_requirements_always_valid(self):
        # SCN-003: 00-requirements → any
        for layer in KDDLayer:
            assert is_layer_violation(KDDLayer.REQUIREMENTS, layer) is False

    def test_same_layer_is_valid(self):
        # SCN-004: same layer
        for layer in KDDLayer:
            assert is_layer_violation(layer, layer) is False

    def test_verification_to_domain(self):
        assert is_layer_violation(KDDLayer.VERIFICATION, KDDLayer.DOMAIN) is False

    def test_domain_to_verification(self):
        assert is_layer_violation(KDDLayer.DOMAIN, KDDLayer.VERIFICATION) is True

    def test_domain_to_experience(self):
        assert is_layer_violation(KDDLayer.DOMAIN, KDDLayer.EXPERIENCE) is True

    def test_experience_to_behavior(self):
        assert is_layer_violation(KDDLayer.EXPERIENCE, KDDLayer.BEHAVIOR) is False

    @pytest.mark.parametrize("origin,dest,expected", [
        (KDDLayer.VERIFICATION, KDDLayer.EXPERIENCE, False),
        (KDDLayer.VERIFICATION, KDDLayer.BEHAVIOR, False),
        (KDDLayer.VERIFICATION, KDDLayer.DOMAIN, False),
        (KDDLayer.EXPERIENCE, KDDLayer.DOMAIN, False),
        (KDDLayer.BEHAVIOR, KDDLayer.DOMAIN, False),
        (KDDLayer.DOMAIN, KDDLayer.BEHAVIOR, True),
        (KDDLayer.DOMAIN, KDDLayer.EXPERIENCE, True),
        (KDDLayer.DOMAIN, KDDLayer.VERIFICATION, True),
        (KDDLayer.BEHAVIOR, KDDLayer.EXPERIENCE, True),
        (KDDLayer.BEHAVIOR, KDDLayer.VERIFICATION, True),
        (KDDLayer.EXPERIENCE, KDDLayer.VERIFICATION, True),
    ])
    def test_all_layer_combinations(self, origin, dest, expected):
        assert is_layer_violation(origin, dest) is expected


class TestDetectLayer:
    def test_all_prefixes(self):
        assert detect_layer("00-requirements/PRD.md") == KDDLayer.REQUIREMENTS
        assert detect_layer("01-domain/entities/X.md") == KDDLayer.DOMAIN
        assert detect_layer("02-behavior/commands/CMD.md") == KDDLayer.BEHAVIOR
        assert detect_layer("03-experience/views/V.md") == KDDLayer.EXPERIENCE
        assert detect_layer("04-verification/criteria/R.md") == KDDLayer.VERIFICATION

    def test_unknown_path(self):
        assert detect_layer("random/path.md") is None

    def test_nested_path(self):
        assert detect_layer("specs/01-domain/entities/Pedido.md") == KDDLayer.DOMAIN


# ---------------------------------------------------------------------------
# BR-MERGE-001 — resolve_node_conflict() / resolve_deletion()
# ---------------------------------------------------------------------------


class TestResolveNodeConflict:
    """BR-MERGE-001: Merge Conflict Resolution — last-write-wins."""

    def test_single_candidate(self):
        result = resolve_node_conflict([
            {"source_hash": "abc", "indexed_at": "2026-02-15T10:00:00"},
        ])
        assert result.winner_index == 0
        assert result.reason == "single"

    def test_identical_hashes(self):
        result = resolve_node_conflict([
            {"source_hash": "abc", "indexed_at": "2026-02-15T10:00:00"},
            {"source_hash": "abc", "indexed_at": "2026-02-15T10:15:00"},
        ])
        assert result.winner_index == 0
        assert result.reason == "identical"

    def test_last_write_wins(self):
        result = resolve_node_conflict([
            {"source_hash": "abc", "indexed_at": "2026-02-15T10:00:00"},
            {"source_hash": "xyz", "indexed_at": "2026-02-15T10:15:00"},
        ])
        assert result.winner_index == 1
        assert result.reason == "last-write-wins"

    def test_three_way_conflict(self):
        result = resolve_node_conflict([
            {"source_hash": "aaa", "indexed_at": "2026-02-15T10:00:00"},
            {"source_hash": "bbb", "indexed_at": "2026-02-15T10:30:00"},
            {"source_hash": "ccc", "indexed_at": "2026-02-15T10:15:00"},
        ])
        assert result.winner_index == 1  # 10:30 is latest
        assert result.reason == "last-write-wins"


class TestResolveDeletion:
    """BR-MERGE-001: Delete-wins."""

    def test_all_present(self):
        deleted, warning = resolve_deletion([True, True])
        assert deleted is False
        assert warning is None

    def test_one_deleted(self):
        deleted, warning = resolve_deletion([True, False])
        assert deleted is True
        assert warning is None

    def test_deleted_with_modification_warning(self):
        deleted, warning = resolve_deletion(
            [True, False],
            modified_after_deletion=True,
        )
        assert deleted is True
        assert warning is not None
        assert "modified" in warning.lower()

    def test_all_deleted(self):
        deleted, warning = resolve_deletion([False, False])
        assert deleted is True
