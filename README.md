# 👑 Monarch — Enterprise-Grade Multi-Agent AI Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq Vision](https://img.shields.io/badge/Groq-Vision_llama--3.2-orange.svg)](https://groq.com/)
[![AWS Cloud](https://img.shields.io/badge/AWS-Aurora_|_S3_|_OpenSearch-ff9900.svg?style=flat&logo=amazon-aws)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Monarch** is an enterprise-grade multi-agent orchestration platform built with **LangGraph (Async)**, **ReAct Tool Planning**, **Agentic RAG (HyDE & Query Decomposition)**, **Multimodal Groq Vision**, **Cognito JWT Auth & RBAC**, **AWS Infrastructure Integrations**, **Enterprise Security & Output Safety**, and **SSE Token Streaming**.

---

## 🏗 System Architecture

```mermaid
flowchart TD
    Client([User / Web Workbench / REST Client]) --> |HTTP / SSE Token Stream| API[FastAPI Backend api.py]
    
    subgraph SecurityAuth ["Security, Auth & Compliance Layer"]
        API --> RateLimiter[Distributed Rate Limiter - ElastiCache Redis / In-Memory]
        RateLimiter --> AuthMiddleware[Cognito JWT Auth & RBAC Middleware]
        AuthMiddleware --> InputGuard[Input Guardrail: PII Masking, Luhn Validation & ML LLM-Judge]
    end

    subgraph Agents ["LangGraph Async Multi-Agent Engine (Agents/)"]
        InputGuard --> Orchestrator["Async Orchestrator Router (router.py)"]
        Orchestrator --> |Structured Decision| RouteSwitch{Route Selector}
        
        RouteSwitch -->|General Reasoning & Tools| Planner["ReAct Planner Agent (planner.py)"]
        RouteSwitch -->|Live Info / Search| Research["Async Research Agent (research.py)"]
        RouteSwitch -->|Document Corpus| RAGNode["Agentic RAG Agent (rag.py)"]
        RouteSwitch -->|Image / Visual Prompt| VisionNode["Groq Vision Agent (vision.py)"]
        RouteSwitch -->|Compound Multi-Hop Query| ParallelNode["Parallel Agent Fan-Out (parallel.py)"]
        
        Planner --> Tools["Agent Tools: Calculator, Datetime, Memory, Code Sandbox"]
        RAGNode --> QueryEngine["Agentic RAG Engine: HyDE, Sub-Query Decomposition, Feedback Rewriting"]
        
        Planner --> Reflection["Reflection Critic Node (reflection.py)"]
        Research --> Reflection
        RAGNode --> Reflection
        VisionNode --> Reflection
        ParallelNode --> Reflection

        Reflection -->|Refinement Needed & Retry <= 2| RouteSwitch
        Reflection -->|Pass / Complete| OutputGuard[Output Safety & Faithfulness Guardrail]
    end

    subgraph AWSInfra ["AWS-Native Cloud Infrastructure Layer"]
        RAGNode --> OpenSearch[Amazon OpenSearch Serverless Vector Store]
        RAGNode --> S3Storage[Amazon S3 Document Storage s3_manager.py]
        API --> AuroraDB[(Amazon Aurora PostgreSQL + pgvector / SQLite)]
        API --> SecretsMgr[AWS Secrets Manager / Local .env]
        API --> AuditLogger[CloudWatch Audit Logger & GDPR Data Retention]
    end

    OutputGuard --> FinalOutput([Client SSE Token Stream + Audit Log])
```

---

## 📁 Repository Directory Structure

```
Monarch/
├── .env                        # Environment API keys & global configurations
├── Dockerfile                  # Container build instructions with OCR & PDF libraries
├── docker-compose.yml          # Multi-service orchestration file
├── pyproject.toml              # Project dependencies & build metadata
├── pytest.ini                  # Pytest configuration & test runner settings
├── requirements.txt            # Python dependencies (LangGraph, Groq, FAISS, PyPDF, asyncpg, boto3, redis, pytest)
├── main.py                     # Primary CLI entrypoint & benchmark harness driver
├── api.py                      # Production FastAPI REST service with SSE streaming & CRUD endpoints
├── index.html                  # Monarch Web Workbench HTML interface
├── static/                     # Web UI assets
│   ├── app.js                  # Frontend REST API integration & image uploader
│   └── style.css               # Glassmorphism dark mode stylesheet
│
├── Agents/                     # LangGraph Async Multi-Agent Workflow Core
│   ├── state.py                # Canonical LangGraph State schema & RouteDecision model
│   ├── router.py               # Async Orchestrator routing node with memory injection
│   ├── planner.py              # ReAct multi-step tool-use planner agent node
│   ├── research.py             # Async live web research agent node
│   ├── rag.py                  # Agentic document RAG agent node
│   ├── vision.py               # Multimodal Groq Vision agent node
│   ├── parallel.py             # Parallel agent fan-out & result merger node
│   ├── reflection.py           # Self-correction reflection critic node
│   ├── graph.py                # LangGraph workflow compiler
│   └── tools/                  # Agent Executable Tools
│       ├── calculator.py       # Safe math AST evaluation tool
│       ├── datetime_tool.py    # UTC system date/time tool
│       ├── memory_tool.py      # User long-term memory search & store tools
│       └── code_executor.py    # Sandboxed Python code execution tool
│
├── RAG/                        # Multimodal Agentic RAG Subsystem
│   ├── embeddings.py           # HuggingFace embeddings wrapper
│   ├── retriever.py            # Hybrid retrieval (FAISS + BM25 + Reciprocal Rank Fusion)
│   ├── manager.py              # Document loader (PDF, DOCX, TXT, OCR) & vector manager
│   └── query_engine.py         # Agentic query engine (HyDE, Sub-Query Decomposition, Query Rewriting)
│
├── auth/                       # Enterprise Authentication & RBAC
│   ├── cognito.py              # Amazon Cognito JWT verification middleware
│   ├── rbac.py                 # Role-based access control (Admin, User, ReadOnly)
│   └── dependencies.py         # FastAPI get_current_user dependency injection
│
├── guardrails/                 # Security, Safety, & Output Verification
│   ├── input_guard.py          # PII masking (Luhn Cards, Emails, Keys) & ML LLM-Judge Classifier
│   └── output_guard.py         # Output safety (Toxicity, Bias, PII Leakage) & Faithfulness verification
│
├── audit/                      # Structured Audit Logging & GDPR Compliance
│   ├── logger.py               # Structured CloudWatch JSON audit logger
│   └── data_retention.py       # GDPR full data erasure engine (DELETE /api/user/{user_id}/data)
│
├── storage/                    # Cloud Storage Integrations
│   └── s3_manager.py           # Amazon S3 raw document manager & presigned URL generator
│
├── infra/                      # Cloud Infrastructure Provisioning
│   └── opensearch.py           # Amazon OpenSearch Serverless collection & k-NN index builder
│
├── SQL/                        # Persistence & Database Repositories
│   ├── schema.sql              # PostgreSQL + pgvector schema
│   ├── db.py                   # Async Aurora PostgreSQL connection pool & SQLite manager
│   ├── repository.py           # MemoryRepository for durable chat & memory storage
│   └── memory_consolidator.py  # Asynchronous background memory fact distillation
│
├── tests/                      # Automated Test Suite (Pytest)
│   ├── conftest.py             # Pytest fixtures & TestClient setup
│   ├── test_input_guard.py     # PII masking & injection unit tests
│   ├── test_output_guard.py    # Faithfulness verification unit tests
│   ├── test_router.py          # Async router unit tests
│   ├── test_rag_manager.py     # RAG ingestion & retrieval unit tests
│   ├── test_rate_limiter.py    # Sliding window rate limiter unit tests
│   ├── test_api.py             # REST API integration tests
│   ├── test_phase2.py          # AWS infrastructure unit tests
│   ├── test_phase3.py          # Tools, HyDE, code execution unit tests
│   └── test_phase4.py          # Auth, Luhn validation, audit & GDPR unit tests
│
└── utils/                      # Utilities & Middleware
    ├── config.py               # AWS Secrets Manager fetcher & Groq model resolver
    ├── logger.py               # Centralized logging instance
    ├── retry.py                # Exponential backoff retry decorator (@llm_retry)
    └── rate_limiter.py         # ElastiCache Redis & in-memory sliding window rate limiter
```

---

## 🌟 Key Technical Highlights

### 1. ⚡ Async Execution & Token-Level SSE Streaming
- All agent nodes operate using non-blocking `async def` with `await llm.ainvoke()`.
- `POST /api/chat/stream` streams token chunks in real-time over Server-Sent Events (`text/event-stream`).

### 2. 🧰 ReAct Tool Planning & Code Execution Sandbox
- Multi-step tool-use planner equipped with safe math evaluator, date/time tools, memory search tools, and Python execution sandbox (`Agents/tools/code_executor.py`).

### 3. 🧠 Agentic RAG (HyDE & Multi-Hop Query Decomposition)
- Uses HyDE (Hypothetical Document Embeddings) and sub-query decomposition to handle multi-step document research queries.

### 4. 🔀 Parallel Agent Fan-Out
- `Agents/parallel.py` dispatches compound queries to Research and RAG nodes concurrently via `asyncio.gather()` and synthesizes findings into a single response.

### 5. 🛡️ Enterprise Security, Auth & GDPR Compliance
- **Cognito JWT Auth & RBAC**: Role-enforced API routes (`Admin`, `User`, `ReadOnly`).
- **PII & ML Injection Defense**: Luhn-validated credit card masking, email/phone redacting, and ML LLM-Judge prompt override classifier.
- **GDPR Data Erasure**: `DELETE /api/user/{user_id}/data` purges database records, chat histories, user memories, and vector index chunks.
- **Audit Logging**: CloudWatch-compatible structured JSON audit logger.

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.11+
- Groq API Key (Console: [console.groq.com](https://console.groq.com))

### 2. Environment Setup

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
VISION_MODEL=llama-3.2-11b-vision-preview

# Optional Cloud Integrations
DATABASE_URL=postgresql://user:pass@aurora-endpoint:5432/monarch
REDIS_URL=redis://localhost:6379/0
S3_DOCUMENTS_BUCKET=monarch-docs-storage
AWS_REGION=us-east-1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 💻 Running & Testing

### 1. Run FastAPI Backend Server
```bash
python main.py --serve-api
```
- Open Web Workbench: `http://localhost:8000`
- Open Swagger Docs: `http://localhost:8000/docs`

### 2. Run Pytest Automated Suite
```bash
pytest tests/ --cov=.
```

---

## 📄 License
This project is licensed under the MIT License.