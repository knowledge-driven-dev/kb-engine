"""Document kind detector."""

import frontmatter
import structlog

from kb_engine.smart.types import DetectionResult, KDDDocumentKind

logger = structlog.get_logger(__name__)


class DocumentKindDetector:
    """Detects the kind of KDD document from content and metadata."""

    # Mapping from kind values to enum
    KIND_MAP = {
        "entity": KDDDocumentKind.ENTITY,
        "use-case": KDDDocumentKind.USE_CASE,
        "rule": KDDDocumentKind.RULE,
        "process": KDDDocumentKind.PROCESS,
        "event": KDDDocumentKind.EVENT,
        "command": KDDDocumentKind.COMMAND,
        "query": KDDDocumentKind.QUERY,
        "adr": KDDDocumentKind.ADR,
        "prd": KDDDocumentKind.PRD,
        "nfr": KDDDocumentKind.NFR,
        "story": KDDDocumentKind.STORY,
        "ui-view": KDDDocumentKind.UI_VIEW,
        "ui-flow": KDDDocumentKind.UI_FLOW,
        "ui-component": KDDDocumentKind.UI_COMPONENT,
        "idea": KDDDocumentKind.IDEA,
        "requirement": KDDDocumentKind.REQUIREMENT,
        "implementation-charter": KDDDocumentKind.IMPLEMENTATION_CHARTER,
    }

    def detect(self, content: str, filename: str | None = None) -> DetectionResult:
        """Detect document kind from content and optional filename.

        Args:
            content: Raw markdown content.
            filename: Optional filename for additional hints.

        Returns:
            DetectionResult with kind, confidence, and detection source.
        """
        log = logger.bind(filename=filename)

        # 1. Try frontmatter 'kind' field (highest confidence)
        try:
            fm = frontmatter.loads(content)
            kind_value = fm.metadata.get("kind", "").lower().strip()

            if kind_value and kind_value in self.KIND_MAP:
                log.debug("detector.frontmatter", kind=kind_value)
                return DetectionResult(
                    kind=self.KIND_MAP[kind_value],
                    confidence=1.0,
                    detected_from="frontmatter",
                )
        except Exception as e:
            log.warning("detector.frontmatter_error", error=str(e))

        # 2. Try filename patterns (medium confidence)
        if filename:
            filename_lower = filename.lower()

            # Check for path patterns
            path_patterns = {
                "entities/": KDDDocumentKind.ENTITY,
                "use-cases/": KDDDocumentKind.USE_CASE,
                "rules/": KDDDocumentKind.RULE,
                "processes/": KDDDocumentKind.PROCESS,
                "events/": KDDDocumentKind.EVENT,
                "adrs/": KDDDocumentKind.ADR,
            }

            for pattern, kind in path_patterns.items():
                if pattern in filename_lower:
                    log.debug("detector.filename_path", kind=kind.value, pattern=pattern)
                    return DetectionResult(
                        kind=kind,
                        confidence=0.7,
                        detected_from="filename",
                    )

            # Check for filename prefixes
            prefix_patterns = {
                "uc-": KDDDocumentKind.USE_CASE,
                "evt-": KDDDocumentKind.EVENT,
                "cmd-": KDDDocumentKind.COMMAND,
                "qry-": KDDDocumentKind.QUERY,
                "adr-": KDDDocumentKind.ADR,
            }

            for prefix, kind in prefix_patterns.items():
                if filename_lower.startswith(prefix):
                    log.debug("detector.filename_prefix", kind=kind.value, prefix=prefix)
                    return DetectionResult(
                        kind=kind,
                        confidence=0.6,
                        detected_from="filename",
                    )

        # 3. Unknown
        log.debug("detector.unknown")
        return DetectionResult(
            kind=KDDDocumentKind.UNKNOWN,
            confidence=0.0,
            detected_from="none",
        )
