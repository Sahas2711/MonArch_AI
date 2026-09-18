"""
In-memory Sliding Window Rate Limiter Middleware for Monarch FastAPI Service.

Enforces configurable rate limits per client IP address across API routes:
  - POST /api/chat   : 20 requests per minute
  - POST /api/ingest : 10 uploads per minute
  - General API      : 60 requests per minute
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from utils.logger import log


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        chat_limit: int = 20,
        ingest_limit: int = 10,
        default_limit: int = 60,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.chat_limit = chat_limit
        self.ingest_limit = ingest_limit
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        # Storage structure: client_ip -> category -> list of timestamps
        self._request_history: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    def _get_limit_and_category(self, path: str) -> Tuple[int, str]:
        if path.startswith("/api/chat"):
            return self.chat_limit, "chat"
        elif path.startswith("/api/ingest"):
            return self.ingest_limit, "ingest"
        else:
            return self.default_limit, "general"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Bypass rate limiting for static assets, root HTML, docs & health check
        if path == "/" or path.startswith("/static") or path == "/api/health" or path in ("/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        limit, category = self._get_limit_and_category(path)
        now = time.time()

        # Clean timestamps older than window_seconds
        timestamps = self._request_history[client_ip][category]
        cutoff = now - self.window_seconds
        valid_timestamps = [ts for ts in timestamps if ts > cutoff]
        self._request_history[client_ip][category] = valid_timestamps

        if len(valid_timestamps) >= limit:
            retry_after = int(self.window_seconds - (now - valid_timestamps[0]))
            log.warning(
                "Rate limit exceeded for client %s on %s (%d/%d requests used in %ds)",
                client_ip,
                path,
                len(valid_timestamps),
                limit,
                self.window_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please wait before retrying.",
                    "limit": limit,
                    "window_seconds": self.window_seconds,
                    "retry_after_seconds": max(1, retry_after),
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )

        # Record request timestamp
        self._request_history[client_ip][category].append(now)

        response = await call_next(request)
        remaining = max(0, limit - len(self._request_history[client_ip][category]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
