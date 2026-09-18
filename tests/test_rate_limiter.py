"""
Unit tests for RateLimiterMiddleware.
"""

from utils.rate_limiter import RateLimiterMiddleware


def test_get_limit_and_category():
    middleware = RateLimiterMiddleware(app=None, chat_limit=5, ingest_limit=2, default_limit=10)
    
    limit, cat = middleware._get_limit_and_category("/api/chat")
    assert limit == 5
    assert cat == "chat"

    limit, cat = middleware._get_limit_and_category("/api/ingest")
    assert limit == 2
    assert cat == "ingest"

    limit, cat = middleware._get_limit_and_category("/api/memories")
    assert limit == 10
    assert cat == "general"
