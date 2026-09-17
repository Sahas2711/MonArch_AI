# Incident Report: INC-2026-001 — API Rate Limiter Spike & HTTP 429 Cascades

- **Incident ID**: INC-2026-001
- **Severity**: High (P2)
- **Component**: FastAPI Gateway (`api.py`, `utils/rate_limiter.py`)
- **Status**: Resolved
- **Date**: 2026-09-17

## 1. Description
During a high-concurrency stress test on `/api/chat`, the sliding-window rate limiter blocked legitimate traffic with HTTP 429 errors. A race condition in cleanup of expired IP timestamps caused thread contention, stalling valid requests.

## 2. Impact
- **Peak Request Rate**: 1,200 req/min
- **Error Rate**: 38% HTTP 429 False Positives
- **P99 Latency Spike**: 4.8s (Normal: 420ms)

## 3. Timeline
- **08:15 UTC**: Stress testing triggered on `/api/chat` endpoint.
- **08:18 UTC**: Monitoring reported elevated HTTP 429 response rate (38%).
- **08:25 UTC**: SRE team identified dictionary lock contention in `utils/rate_limiter.py`.
- **08:45 UTC**: Hotfix deployed enforcing per-IP `asyncio.Lock()`.
- **09:00 UTC**: Traffic returned to normal baseline.

## 4. Root Cause Analysis
The `RateLimiterMiddleware` used a single un-synchronized dictionary across async requests. High concurrent mutations triggered dictionary resizing exceptions and lock contention.

## 5. Remediation & Action Items
1. Refactored `utils/rate_limiter.py` to use `asyncio.Lock()` per IP window.
2. Implemented automatic garbage collection for inactive client IPs every 60 seconds.
3. Added `Retry-After` header standardization in FastAPI exception handling.
