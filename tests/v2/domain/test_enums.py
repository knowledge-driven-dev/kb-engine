"""Tests for kdd.domain.enums."""

from kdd.domain.enums import (
    DocumentStatus,
    EdgeType,
    IndexLevel,
    KDDKind,
    KDDLayer,
    QueryStatus,
    RetrievalStrategy,
)


class TestKDDKind:
    """KDDKind covers the 15 artifact types from PRD-KBEngine."""

    def test_has_15_members(self):
        assert len(KDDKind) == 15

    def test_all_values_are_lowercase_kebab(self):
        for kind in KDDKind:
            assert kind.value == kind.value.lower()
            assert " " not in kind.value

    def test_string_serialisation(self):
        assert KDDKind.ENTITY == "entity"
        assert KDDKind.USE_CASE == "use-case"
        assert KDDKind.BUSINESS_RULE == "business-rule"

    def test_from_string(self):
        assert KDDKind("entity") is KDDKind.ENTITY
        assert KDDKind("command") is KDDKind.COMMAND
        assert KDDKind("adr") is KDDKind.ADR

    def test_expected_kinds(self):
        expected = {
            "entity", "event", "business-rule", "business-policy",
            "cross-policy", "command", "query", "process", "use-case",
            "ui-view", "ui-component", "requirement", "objective",
            "prd", "adr",
        }
        assert {k.value for k in KDDKind} == expected


class TestKDDLayer:
    """KDDLayer has 5 values with correct numeric ordering."""

    def test_has_5_members(self):
        assert len(KDDLayer) == 5

    def test_numeric_ordering(self):
        assert KDDLayer.REQUIREMENTS.numeric == 0
        assert KDDLayer.DOMAIN.numeric == 1
        assert KDDLayer.BEHAVIOR.numeric == 2
        assert KDDLayer.EXPERIENCE.numeric == 3
        assert KDDLayer.VERIFICATION.numeric == 4

    def test_ordering_ascending(self):
        layers = list(KDDLayer)
        for i in range(len(layers) - 1):
            assert layers[i].numeric < layers[i + 1].numeric

    def test_string_values(self):
        assert KDDLayer.REQUIREMENTS == "00-requirements"
        assert KDDLayer.DOMAIN == "01-domain"
        assert KDDLayer.VERIFICATION == "04-verification"


class TestEdgeType:
    """EdgeType covers 16 structural edge types from GraphEdge spec."""

    def test_has_16_members(self):
        assert len(EdgeType) == 16

    def test_all_screaming_snake_case(self):
        for et in EdgeType:
            assert et.value == et.value.upper()
            assert " " not in et.value

    def test_key_types_exist(self):
        assert EdgeType.WIKI_LINK.value == "WIKI_LINK"
        assert EdgeType.EMITS.value == "EMITS"
        assert EdgeType.UC_APPLIES_RULE.value == "UC_APPLIES_RULE"
        assert EdgeType.CROSS_DOMAIN_REF.value == "CROSS_DOMAIN_REF"


class TestIndexLevel:
    def test_has_3_levels(self):
        assert len(IndexLevel) == 3

    def test_values(self):
        assert IndexLevel.L1 == "L1"
        assert IndexLevel.L2 == "L2"
        assert IndexLevel.L3 == "L3"


class TestRetrievalStrategy:
    def test_has_4_strategies(self):
        assert len(RetrievalStrategy) == 4

    def test_values(self):
        assert RetrievalStrategy.GRAPH == "graph"
        assert RetrievalStrategy.SEMANTIC == "semantic"
        assert RetrievalStrategy.HYBRID == "hybrid"
        assert RetrievalStrategy.IMPACT == "impact"


class TestDocumentStatus:
    def test_has_5_states(self):
        assert len(DocumentStatus) == 5

    def test_lifecycle_states(self):
        values = {s.value for s in DocumentStatus}
        assert values == {"detected", "parsing", "indexed", "stale", "deleted"}


class TestQueryStatus:
    def test_has_4_states(self):
        assert len(QueryStatus) == 4
