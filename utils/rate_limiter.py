"""
In-memory Sliding Window Rate Limiter Middleware for Monarch FastAPI Service.

Enforces configurable rate limits per client IP address across API routes:
  - POST /api/chat   : 20 requests per minute
  - POST /api/ingest : 10 uploads per minute
  - General API      : 60 requests per minute
"""

import os
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from utils.logger import log

REDIS_URL = os.getenv("REDIS_URL")
_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None and REDIS_URL:
        try:
            import redis.asyncio as redis

            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            log.info("Initialized Redis connection for distributed rate limiting.")
        except Exception as exc:
            log.warning("Could not connect to Redis (%s). Falling back to in-memory rate limiting.", exc)
    return _redis_client


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
        # Fallback in-memory storage structure: client_ip -> category -> list of timestamps
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

        r = await _get_redis()
        if r:
            # Distributed Redis sliding window using sorted sets
            key = f"rate:{client_ip}:{category}"
            cutoff = now - self.window_seconds
            try:
                pipeline = r.pipeline()
                pipeline.zremrangebyscore(key, 0, cutoff)
                pipeline.zcard(key)
                pipeline.zadd(key, {str(now): now})
                pipeline.expire(key, self.window_seconds + 5)
                results = await pipeline.execute()

                count = results[1]
                if count >= limit:
                    log.warning("Redis rate limit exceeded for %s on %s (%d/%d)", client_ip, path, count, limit)
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Please wait before retrying.", "limit": limit},
                        headers={"Retry-After": str(self.window_seconds)},
                    )
                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count - 1))
                return response
            except Exception as exc:
                log.warning("Redis rate limiter error (%s); using in-memory fallback.", exc)

        # Fallback: In-memory sliding window
        timestamps = self._request_history[client_ip][category]
        cutoff = now - self.window_seconds
        valid_timestamps = [ts for ts in timestamps if ts > cutoff]
        self._request_history[client_ip][category] = valid_timestamps

        if len(valid_timestamps) >= limit:
            retry_after = int(self.window_seconds - (now - valid_timestamps[0]))
            log.warning("Rate limit exceeded for client %s on %s", client_ip, path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before retrying.", "limit": limit},
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._request_history[client_ip][category].append(now)

        response = await call_next(request)
        remaining = max(0, limit - len(self._request_history[client_ip][category]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
