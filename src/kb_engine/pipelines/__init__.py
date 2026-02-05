"""Processing pipelines for KB-Engine."""

from kb_engine.pipelines.indexation import IndexationPipeline
from kb_engine.pipelines.inference import InferencePipeline

__all__ = ["IndexationPipeline", "InferencePipeline"]
