"""Authentication middleware."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Verify API key if authentication is enabled.

    TODO: Implement actual API key validation.
    """
    # Placeholder - would validate against stored keys
    if api_key is None:
        # For now, allow unauthenticated access
        return "anonymous"

    # TODO: Validate API key
    return api_key
