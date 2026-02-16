"""Tests for kdd.application.extractors.registry."""

from kdd.application.extractors.registry import ExtractorRegistry, create_default_registry
from kdd.domain.enums import KDDKind


class TestExtractorRegistry:
    def test_register_and_get(self):
        from kdd.application.extractors.kinds.entity import EntityExtractor

        registry = ExtractorRegistry()
        ext = EntityExtractor()
        registry.register(ext)
        assert registry.get(KDDKind.ENTITY) is ext

    def test_get_unknown_returns_none(self):
        registry = ExtractorRegistry()
        assert registry.get(KDDKind.EVENT) is None

    def test_len(self):
        registry = ExtractorRegistry()
        assert len(registry) == 0
        from kdd.application.extractors.kinds.entity import EntityExtractor
        registry.register(EntityExtractor())
        assert len(registry) == 1


class TestCreateDefaultRegistry:
    def test_has_15_extractors(self):
        registry = create_default_registry()
        assert len(registry) == 15

    def test_finds_correct_extractor_per_kind(self):
        registry = create_default_registry()
        assert registry.registered_kinds == set(KDDKind)

    def test_each_extractor_has_matching_kind(self):
        registry = create_default_registry()
        for kind in registry.registered_kinds:
            ext = registry.get(kind)
            assert ext is not None
            assert ext.kind == kind
