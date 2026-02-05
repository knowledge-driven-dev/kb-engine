"""Factory for creating extraction pipelines."""

from kb_engine.extraction.config import ExtractionConfig
from kb_engine.extraction.extractors.frontmatter import FrontmatterExtractor
from kb_engine.extraction.extractors.llm import LLMExtractor
from kb_engine.extraction.extractors.pattern import PatternExtractor
from kb_engine.extraction.pipeline import ExtractionPipeline


class ExtractionPipelineFactory:
    """Factory for creating configured extraction pipelines."""

    def __init__(self, config: ExtractionConfig | None = None) -> None:
        self._config = config or ExtractionConfig()

    def create_pipeline(self) -> ExtractionPipeline:
        """Create an extraction pipeline with configured extractors."""
        pipeline = ExtractionPipeline(config=self._config)

        # Register extractors based on configuration
        if self._config.enable_frontmatter_extraction:
            pipeline.register_extractor(FrontmatterExtractor())

        if self._config.enable_pattern_extraction:
            pipeline.register_extractor(PatternExtractor())

        if self._config.enable_llm_extraction and self._config.use_llm:
            pipeline.register_extractor(
                LLMExtractor(
                    model=self._config.llm_model,
                    temperature=self._config.llm_temperature,
                )
            )

        return pipeline
