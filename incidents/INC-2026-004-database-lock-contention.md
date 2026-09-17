# Incident Report: INC-2026-004 — SQLite Database Lock Contention in Fact Distillation

- **Incident ID**: INC-2026-004
- **Severity**: Medium (P3)
- **Component**: Memory Subsystem (`SQL/repository.py`, `SQL/memory_consolidator.py`)
- **Status**: Resolved
- **Date**: 2026-09-17

## 1. Description
Asynchronous background memory distillation tasks produced `sqlite3.OperationalError: database is locked` errors during concurrent user message saving.

## 2. Impact
- **Failed Background Tasks**: 18% of fact distillation jobs
- **Database Lock Wait Time**: >5,000ms
- **Impact**: User memories delayed in semantic storage

## 3. Timeline
- **16:10 UTC**: Background task error rate spiked on memory distillation.
- **16:20 UTC**: Log analysis confirmed SQLite write contention between main thread and FastAPI background worker.
- **16:35 UTC**: Enabled Write-Ahead Logging (WAL) mode in `SQL/db.py`.
- **16:45 UTC**: Lock errors dropped to 0%.

## 4. Root Cause Analysis
SQLite in default journal mode defaults to single-writer access. Concurrent background workers in FastAPI wrote to `monarch.db` simultaneously without WAL (Write-Ahead Logging) mode enabled.

## 5. Remediation & Action Items
1. Updated `SQL/db.py` initialization to enable `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
2. Wrapped memory repository database writes in retry decorator `@db_retry(max_retries=3)`.
3. Separated read queries from memory distillation write transactions.
