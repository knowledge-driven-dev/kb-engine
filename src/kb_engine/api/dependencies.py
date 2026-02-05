"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends, Request

from kb_engine.config import Settings, get_settings
from kb_engine.services.indexing import IndexingService
from kb_engine.services.inference import InferenceService


def get_settings_dep() -> Settings:
    """Get application settings."""
    return get_settings()


async def get_indexing_service(request: Request) -> IndexingService:
    """Get the indexing service from app state."""
    # TODO: Return actual service from app.state
    raise NotImplementedError("Indexing service not initialized")


async def get_inference_service(request: Request) -> InferenceService:
    """Get the inference service from app state."""
    # TODO: Return actual service from app.state
    raise NotImplementedError("Inference service not initialized")


# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
IndexingServiceDep = Annotated[IndexingService, Depends(get_indexing_service)]
InferenceServiceDep = Annotated[InferenceService, Depends(get_inference_service)]
