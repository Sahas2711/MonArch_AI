# Monarch — System Architecture

## Overview

Monarch is a multi-agent AI system that investigates production incidents by ingesting scattered evidence (logs, PDFs, screenshots) and producing a verified, traceable root-cause report.

## High-Level Architecture

```
User (SRE Workstation UI)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                 FastAPI Gateway (api.py)             │
│  POST /api/chat  │  POST /api/ingest  │  GET /api/health  │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│          LangGraph Investigation Pipeline           │
│                    (Agents/graph.py)                 │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Router   │  │ Planner  │  │  Research Agent  │  │
│  │(router.py)│  │(planner) │  │  (research.py)   │  │
│  └────┬─────┘  └──────────┘  └──────────────────┘  │
│       │                                              │
│  ┌────▼─────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ RAG Agent │  │  Vision  │  │ Reflection Critic│  │
│  │ (rag.py)  │  │ (vision) │  │ (reflection.py)  │  │
│  └────┬─────┘  └──────────┘  └──────────────────┘  │
│       │                                              │
│  ┌────▼─────────────────────────────────────────┐   │
│  │           Evidence Fusion Engine              │   │
│  │  evidence_chain.py │ timeline.py │ contradiction.py│
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              Data & Storage Layer                    │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  FAISS   │  │  SQLite  │  │    AWS S3        │  │
│  │ + BM25   │  │ (local)  │  │ (snapshots)      │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. FastAPI Gateway (`api.py`)

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Execute multi-agent investigation query |
| `/api/ingest` | POST | Upload evidence files (logs, PDFs, images) |
| `/api/memories` | GET/POST | Manage long-term memory facts |
| `/api/health` | GET | System health, model status, LangSmith state |
| `/api/demo-incident` | POST | Load pre-built demo incident (INC-042) |
| `/api/report` | POST | Generate executive incident report |

### 2. Agent Pipeline (`Agents/`)

| Agent | File | Purpose |
|---|---|---|
| **Router** | `router.py` | Classifies query and dispatches to appropriate agent |
| **Planner** | `planner.py` | General reasoning without external data |
| **Research** | `research.py` | Live web search via DuckDuckGo |
| **RAG** | `rag.py` | Retrieves from ingested document vector store |
| **Vision** | `vision.py` | Analyzes images via Groq Vision (llama-3.2) |
| **Reflection** | `reflection.py` | Self-correction loop (up to 2 retries) |

### 3. RAG System (`RAG/`)

| Module | Purpose |
|---|---|
| `manager.py` | Orchestrates hybrid retrieval (FAISS + BM25) |
| `retriever.py` | Vector similarity search with FAISS |
| `embeddings.py` | Sentence-transformers embedding generation |

**Retrieval Strategy:** Reciprocal Rank Fusion (RRF) combining:
- Dense vectors (FAISS with `all-MiniLM-L6-v2`)
- Sparse keywords (BM25 from `rank-bm25`)

### 4. Post-Investigation Enrichment (`utils/`)

| Module | Purpose |
|---|---|
| `evidence_chain.py` | Assigns deterministic Evidence IDs (E001, E002...) |
| `timeline.py` | Parses timestamps into chronological scrubber |
| `contradiction.py` | Competing hypotheses audit (A vs B) |

### 5. Memory System (`SQL/`)

| Table | Purpose |
|---|---|
| `chats` | Chat session metadata |
| `messages` | Timestamped conversation history (episodic) |
| `user_memories` | Long-term durable facts (semantic, pgvector) |
| `chat_summaries` | Consolidated conversation summaries |

### 6. MCP Server (`MCP/server.py`)

Exposes tool capabilities over Streamable-HTTP (`http://127.0.0.1:8000/mcp`) for external LLM integrations via FastMCP.

## Data Flow

```
1. User uploads evidence files
   → Ingest Engine parses (logs, PDFs, images)
   → Assigns Evidence IDs (E001-E005)
   → Indexes into FAISS + BM25 vector store

2. User asks investigation question
   → Router classifies query type
   → Dispatches to appropriate agent(s)
   → Agent retrieves relevant evidence via RAG
   → Vision agent analyzes screenshots/images

3. Evidence Fusion
   → Combines findings from all agents
   → Builds evidence chain with source citations
   → Generates chronological timeline
   → Runs contradiction audit

4. Reflection & Verification
   → Critic reviews findings (up to 2 retries)
   → Produces verified root cause statement
   → Assigns confidence score

5. Output
   → Returns investigation report to UI
   → Optionally persists snapshot to AWS S3
```

## Technology Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI + Uvicorn |
| Agent Orchestration | LangGraph + LangChain |
| LLM Provider | Groq (auto-fallback) |
| Embeddings | sentence-transformers |
| Vector Store | FAISS |
| Keyword Search | BM25 (rank-bm25) |
| Document Processing | pypdf, python-docx, pytesseract |
| Database | SQLite (dev) / PostgreSQL+pgvector (prod) |
| Cloud Storage | AWS S3 |
| Observability | LangSmith |
| Evaluation | DeepEval |
| Containerization | Docker + docker-compose |
