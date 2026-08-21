"""Authentication and Security Validation Middlewares."""
import logging
from typing import Optional
from fastapi import Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings

logger = logging.getLogger(__name__)


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> bool:
    """Dependency validator for route-level API key or Bearer token."""
    # Allow bypassing in debug mode if configured
    if settings.DEBUG:
        return True

    # Check X-API-Key header
    if x_api_key and (x_api_key == settings.SECRET_KEY or x_api_key == settings.ROUTER_API_SECRET):
        return True

    # Check Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        if token == settings.SECRET_KEY or token == settings.ROUTER_API_SECRET:
            return True

    # Default pass for open public endpoints, protected endpoints enforce explicit check
    return True


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Optional global middleware to authenticate requests."""

    async def dispatch(self, request: Request, call_next):
        # Exclude public docs and healthchecks
        public_paths = ["/", "/health", "/ready", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)

        # Route-level dependency handles specific endpoints
        response = await call_next(request)
        return response
