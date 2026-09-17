# Incident Report: INC-2026-002 — Groq API Model Deprecation & Resolution Fallback

- **Incident ID**: INC-2026-002
- **Severity**: Critical (P1)
- **Component**: LLM Core & Config (`utils/config.py`, `Agents/router.py`)
- **Status**: Resolved
- **Date**: 2026-09-17

## 1. Description
Groq deprecated the legacy `llama-3.1-70b-versatile` model endpoint. Initial API calls threw uncaught `NotFoundError` exceptions, rendering the multi-agent orchestrator non-functional.

## 2. Impact
- **Downtime Duration**: 14 minutes
- **Impacted Services**: All Agent Workflows (`/api/chat`, CLI)
- **Failed Invocations**: 840 chat requests

## 3. Timeline
- **14:02 UTC**: Groq model deprecation took effect upstream.
- **14:03 UTC**: Alerts triggered on 100% agent routing execution failure.
- **14:10 UTC**: On-call engineer identified `groq.NotFoundError` in application logs.
- **14:16 UTC**: Deployed `_resolve_model()` helper to query Groq model list dynamically.
- **14:20 UTC**: Incident closed; automated model resolution active.

## 4. Root Cause Analysis
`utils/config.py` loaded `GROQ_MODEL` directly from `.env` without dynamic validation against Groq's active `/v1/models` catalog endpoint.

## 5. Remediation & Action Items
1. Implemented `_resolve_model()` in `utils/config.py` that queries Groq model catalog at startup.
2. Defined fallback priority chain: `openai/gpt-oss-20b` -> `llama-3.3-70b-versatile` -> `qwen/qwen3.6-27b`.
3. Added auto-logging warning when fallback model auto-resolution triggers.
