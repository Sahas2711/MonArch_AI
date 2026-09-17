# Monarch — Incident Case Studies

Monarch is evaluated against 5 synthetic incident scenarios that test multi-agent investigation capabilities across different failure modes.

## Incident Summary

| ID | Title | Severity | Component |
|---|---|---|---|
| INC-2026-001 | API Rate Limiter Spike & HTTP 429 Cascades | High (P2) | FastAPI Gateway |
| INC-2026-002 | Groq API Model Deprecation & Fallback | Critical (P1) | LLM Core |
| INC-2026-003 | FAISS Vector Store Index Corruption | High (P2) | RAG System |
| INC-2026-004 | SQLite Database Lock Contention | Medium (P3) | SQL Memory |
| INC-2026-005 | LangSmith Telemetry Thread Pool Leak | Medium (P3) | Observability |

---

## INC-2026-001: API Rate Limiter Spike

**Component:** `api.py`, `utils/rate_limiter.py`

**Problem:** Sliding-window rate limiter blocked legitimate traffic with HTTP 429 errors during high-concurrency stress tests.

**Root Cause:** Single un-synchronized dictionary across async requests caused race conditions during concurrent mutations.

**Resolution:**
- Refactored to use `asyncio.Lock()` per IP window
- Added automatic garbage collection for inactive IPs
- Standardized `Retry-After` header in exception handling

---

## INC-2026-002: Groq Model Deprecation

**Component:** `utils/config.py`, `Agents/router.py`

**Problem:** Primary Groq model was deprecated, causing immediate application failure.

**Root Cause:** Hard-coded model name without availability validation.

**Resolution:**
- Implemented `_resolve_model()` with Groq API model listing
- Added priority-ordered fallback chain
- Auto-switches to nearest available model

---

## INC-2026-003: FAISS Index Corruption

**Component:** `RAG/retriever.py`, `RAG/embeddings.py`

**Problem:** FAISS index became corrupted during concurrent ingestion, causing retrieval failures.

**Root Cause:** No file-locking mechanism on FAISS index writes.

**Resolution:**
- Added file-level locking for index writes
- Implemented index integrity verification on load
- Added automatic rebuild from source documents

---

## INC-2026-004: Database Lock Contention

**Component:** `SQL/db.py`, `SQL/repository.py`

**Problem:** SQLite database lock contention during concurrent memory consolidation.

**Root Cause:** Long-running transactions holding locks during summarization.

**Resolution:**
- Implemented WAL (Write-Ahead Logging) mode
- Added transaction timeout limits
- Split consolidation into smaller atomic operations

---

## INC-2026-005: LangSmith Thread Pool Leak

**Component:** `utils/config.py`, tracing setup

**Problem:** LangSmith trace exporter accumulated threads, causing memory growth.

**Root Cause:** Trace exporter threads not properly cleaned up on shutdown.

**Resolution:**
- Added proper thread pool shutdown in lifespan handler
- Implemented trace buffer flushing on application exit
- Added health check for thread pool status

---

## Running the Demo

### Load Demo Incident

```bash
curl -X POST http://localhost:8000/api/demo-incident
```

### Sample Investigation Query

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did checkout start failing after deployment v2.4?"}'
```

### Evidence Files

The demo incident (INC-042) includes:

| File | Type | Purpose |
|---|---|---|
| `deployment.log` | Text | Deployment timeline and events |
| `application.log` | Text | Application errors and stack traces |
| `database.log` | Text | Database query failures |
| `incident_report.md` | Markdown | Human-written incident summary |
| `monitoring_dashboard.png` | Image | Dashboard screenshot (OCR analyzed) |
