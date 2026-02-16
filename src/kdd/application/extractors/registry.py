"""Extractor registry — maps KDDKind to extractor instances.

Auto-registers all extractors when the kinds sub-package is imported.
"""

from __future__ import annotations

from kdd.application.extractors.base import Extractor
from kdd.domain.enums import KDDKind


class ExtractorRegistry:
    """Registry that maps :class:`KDDKind` to :class:`Extractor` instances."""

    def __init__(self) -> None:
        self._extractors: dict[KDDKind, Extractor] = {}

    def register(self, extractor: Extractor) -> None:
        """Register an extractor for its ``kind``."""
        self._extractors[extractor.kind] = extractor

    def get(self, kind: KDDKind) -> Extractor | None:
        """Return the extractor for *kind*, or ``None``."""
        return self._extractors.get(kind)

    @property
    def registered_kinds(self) -> set[KDDKind]:
        return set(self._extractors.keys())

    def __len__(self) -> int:
        return len(self._extractors)


def create_default_registry() -> ExtractorRegistry:
    """Create a registry pre-loaded with all 15 extractors."""
    from kdd.application.extractors.kinds.adr import ADRExtractor
    from kdd.application.extractors.kinds.business_policy import PolicyExtractor
    from kdd.application.extractors.kinds.business_rule import RuleExtractor
    from kdd.application.extractors.kinds.command import CommandExtractor
    from kdd.application.extractors.kinds.cross_policy import CrossPolicyExtractor
    from kdd.application.extractors.kinds.entity import EntityExtractor
    from kdd.application.extractors.kinds.event import EventExtractor
    from kdd.application.extractors.kinds.objective import ObjectiveExtractor
    from kdd.application.extractors.kinds.prd import PRDExtractor
    from kdd.application.extractors.kinds.process import ProcessExtractor
    from kdd.application.extractors.kinds.query import QueryExtractor
    from kdd.application.extractors.kinds.requirement import RequirementExtractor
    from kdd.application.extractors.kinds.ui_component import UIComponentExtractor
    from kdd.application.extractors.kinds.ui_view import UIViewExtractor
    from kdd.application.extractors.kinds.use_case import UseCaseExtractor

    registry = ExtractorRegistry()
    registry.register(EntityExtractor())
    registry.register(EventExtractor())
    registry.register(RuleExtractor())
    registry.register(PolicyExtractor())
    registry.register(CrossPolicyExtractor())
    registry.register(CommandExtractor())
    registry.register(QueryExtractor())
    registry.register(ProcessExtractor())
    registry.register(UseCaseExtractor())
    registry.register(UIViewExtractor())
    registry.register(UIComponentExtractor())
    registry.register(RequirementExtractor())
    registry.register(ObjectiveExtractor())
    registry.register(PRDExtractor())
    registry.register(ADRExtractor())
    return registry
