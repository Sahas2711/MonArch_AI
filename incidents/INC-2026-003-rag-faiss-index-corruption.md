# Incident Report: INC-2026-003 — FAISS Vector Store Index Out-Of-Memory

- **Incident ID**: INC-2026-003
- **Severity**: Critical (P1)
- **Component**: Multimodal RAG (`RAG/manager.py`, `RAG/embeddings.py`)
- **Status**: Resolved
- **Date**: 2026-09-17

## 1. Description
Ingestion of a 250MB PDF document containing embedded high-resolution graphics caused worker process crash due to Out-Of-Memory (OOM) killer terminating the FastAPI container.

## 2. Impact
- **Memory Consumption Peak**: 4.2 GB RAM (Limit: 2.0 GB)
- **Container Restarts**: 3 cycles
- **Ingestion Backlog**: 42 pending documents

## 3. Timeline
- **11:30 UTC**: User submitted 250MB document via `/api/ingest`.
- **11:32 UTC**: Container memory breached 2GB threshold; SIGKILL sent by kernel.
- **11:35 UTC**: Container auto-restarted and re-attempted failed ingestion queue.
- **11:45 UTC**: Applied chunk splitting boundaries and batch size limits in `RAGAgentManager`.
- **12:00 UTC**: Service stabilized with batch embedding streaming.

## 4. Root Cause Analysis
`RAGAgentManager.ingest()` attempted to load all extracted text into memory at once without streaming batch processing, while HuggingFace embeddings were initialized with unbounded batch sizes.

## 5. Remediation & Action Items
1. Constrained `RecursiveCharacterTextSplitter` chunk size to 800 tokens with 120 token overlap.
2. Updated HuggingFace embeddings wrapper (`RAG/embeddings.py`) to process vector embeddings in sub-batches of 32 chunks.
3. Configured Docker container memory limits with graceful garbage collection hooks.
