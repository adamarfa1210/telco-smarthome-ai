"""Sliding-Window In-Memory Rate Limiter Middleware."""
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter using a sliding window counter per client IP."""

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.clients: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip health endpoints
        if request.url.path in ["/health", "/ready", "/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - 60.0

        # Clean old timestamps
        self.clients[client_ip] = [t for t in self.clients[client_ip] if t > window_start]

        if len(self.clients[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute allowed."
                }
            )

        self.clients[client_ip].append(now)
        response = await call_next(request)
        return response
