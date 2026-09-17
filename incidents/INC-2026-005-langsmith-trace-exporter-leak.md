# Incident Report: INC-2026-005 — LangSmith Telemetry Exporter Thread Pool Leak

- **Incident ID**: INC-2026-005
- **Severity**: Medium (P3)
- **Component**: Telemetry & Observability (`utils/config.py`, `api.py`)
- **Status**: Resolved
- **Date**: 2026-09-17

## 1. Description
Long-running FastAPI backend deployments exhibited steady memory leak (~15MB/hour) caused by un-reclaimed background threads from the LangChain/LangSmith tracing exporter.

## 2. Impact
- **Leaked Threads**: 120 background HTTP worker threads over 8 hours
- **Memory Growth Rate**: +15.4 MB/hour
- **Process Latency Increase**: +85ms over 12 hours

## 3. Timeline
- **02:00 UTC**: Memory leak detection alert triggered on staging environment.
- **05:30 UTC**: Thread dump indicated orphaned HTTP connection pool threads attached to LangSmith tracer.
- **06:15 UTC**: Refactored tracer setup to reuse global singleton client in `utils/config.py`.
- **06:30 UTC**: Memory footprint stabilized permanently.

## 4. Root Cause Analysis
LangSmith tracing background worker created a new thread pool instance on every graph invocation when `LANGCHAIN_TRACING_V2=true` instead of reusing a global singleton client session.

## 5. Remediation & Action Items
1. Initialized global LangSmith client in `utils/config.py` during module startup.
2. Added proper shutdown hooks in FastAPI `lifespan` context manager (`api.py`) to flush pending traces cleanly.
3. Validated zero thread leaks after 10,000 synthetic chat executions.
