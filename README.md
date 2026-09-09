# 👑 Wemboo (Monarch) — Enterprise-Grade Multi-Agent AI Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq Vision](https://img.shields.io/badge/Groq-Vision_llama--3.2-orange.svg)](https://groq.com/)
[![AWS Cloud](https://img.shields.io/badge/AWS-EC2_|_S3_|_SSM_|_CloudWatch-ff9900.svg?style=flat&logo=amazon-aws)](https://aws.amazon.com/)
[![AWS Cost](https://img.shields.io/badge/AWS_Cost-$0--$5/month-brightgreen.svg)](https://aws.amazon.com/free/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Wemboo (powered by the Monarch Engine)** is a production-grade, horizontally scalable multi-agent AI orchestration platform. Engineered with **LangGraph (Async)**, **ReAct Tool-Use Planning**, **Agentic RAG (HyDE & Query Decomposition)**, **Multimodal Vision**, **Cognito JWT Auth & RBAC**, **CloudWatch Observability**, and **Real-Time Token Streaming (SSE)**.

Built specifically for AWS-native deployment on the **$0–$5/month Free Tier Stack** while targeting top scores across **"Build It"**, **"Ship It"**, and **"Best UI"** tracks.

---

## 🏗 System Architecture

```mermaid
flowchart TD
    Client([User / Web Workbench / REST Client]) --> |HTTP / SSE Token Stream| API[FastAPI Backend api.py]
    
    subgraph SecurityAuth ["Security, Auth & Compliance Layer"]
        API --> RateLimiter[Distributed Rate Limiter - ElastiCache Redis / In-Memory]
        RateLimiter --> AuthMiddleware[Amazon Cognito JWT Auth & RBAC Middleware]
        AuthMiddleware --> InputGuard[Input Guardrail: PII Masking, Luhn Validation & ML LLM-Judge]
    end

    subgraph Agents ["LangGraph Async Multi-Agent Engine (Agents/)"]
        InputGuard --> Orchestrator["Async Orchestrator Router (router.py)"]
        Orchestrator --> |Structured Decision| RouteSwitch{Route Selector}
        
        RouteSwitch -->|General Reasoning & Tools| Planner["ReAct Planner Agent (planner.py)"]
        RouteSwitch -->|Live Info / Web Search| Research["Async Research Agent (research.py)"]
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

    subgraph AWSInfra ["AWS-Native Cloud Infrastructure Layer ($0–$5/mo Stack)"]
        RAGNode --> S3Storage[Amazon S3 Document Store s3_manager.py]
        RAGNode --> VectorStore[(Persistent FAISS / OpenSearch Vector Store)]
        API --> SQLiteDB[(Persistent SQLite on EBS / Aurora PostgreSQL)]
        API --> SecretsMgr[AWS SSM Parameter Store / Secrets Manager]
        API --> AuditLogger[CloudWatch Logs, Metrics & Audit Trail]
    end

    OutputGuard --> FinalOutput([Client SSE Token Stream + Audit Event])
```

---

## 💰 The $0–$5/Month AWS Stack (Cost-Optimized)

Monarch utilizes AWS Free Tier services and low-cost serverless resources without sacrificing enterprise architecture:

| AWS Service | Role in Monarch | Free Tier Allowance | Effective Cost |
| :--- | :--- | :--- | :--- |
| **EC2 `t3.micro`** | Monarch API backend & LangGraph runtime | 750 hours/month (12 mos) | **$0.00** |
| **EBS (20GB gp3)** | Persistent SQLite database (`monarch.db`) & FAISS index | 30 GB free | **$0.00** |
| **Amazon S3** | Raw document store (`s3://monarch-docs`) & frontend assets | 5 GB storage + 20K GETs | **$0.00** |
| **Amazon CloudFront** | Global CDN for fast static frontend distribution | 1 TB data transfer/month | **$0.00** |
| **SSM Parameter Store** | Secure API key & secret retrieval | Standard tier: Free forever | **$0.00** |
| **Amazon CloudWatch** | Structured audit logging & operational metrics | 5 GB logs + 10 metrics | **$0.00** |
| **Amazon Cognito** | User directory, JWT token issuance & RBAC | 50,000 MAU free tier | **$0.00** |
| **Groq API / Bedrock** | Ultra-low latency LLM generation (Bedrock fallback) | Free Groq tier / Token pay | **$0.00 – $5.00** |
| **TOTAL** | **Full Production Deployment** | — | **$0 – $5/month** |

---

## 🏆 Hackathon Winning Track Alignment

* **Track 1: "Build It" (Open-source AWS Stack)**: Integrates Amazon OpenSearch vector indexing templates, AWS SAM-compatible sandboxed code execution, and modular Infrastructure-as-Code.
* **Track 2: "Ship It" (Live Production Deployment)**: Production-ready EC2 container deployment with EBS disk persistence, CloudFront CDN, CloudWatch metrics, and one-command deployment (`./deploy.sh`).
* **Track 3: "Best UI"**: Modern dark mode glassmorphism Web Workbench with typewriter-style Server-Sent Events (SSE) token streaming and drag-and-drop multimodal document uploads.

---

## 📁 Repository Directory Structure

```
Wemboo/
├── .env                        # Environment API keys & configurations
├── Dockerfile                  # Container build instructions with OCR & PDF libraries
├── docker-compose.yml          # Multi-container orchestration file
├── deploy.sh                   # One-command automated deployment script
├── pyproject.toml              # Dependencies and build metadata
├── pytest.ini                  # Pytest configuration & test runner settings
├── requirements.txt            # Python dependencies (LangGraph, Groq, FAISS, PyPDF, etc.)
├── main.py                     # CLI application entrypoint & benchmark test runner
├── api.py                      # Production FastAPI REST service with SSE streaming & CRUD endpoints
├── index.html                  # Monarch Web Workbench HTML interface
├── static/                     # Web UI assets
│   ├── app.js                  # Frontend REST API integration & image uploader
│   └── style.css               # Glassmorphism dark mode stylesheet
│
├── Agents/                     # LangGraph Async Multi-Agent Workflow Core
│   ├── state.py                # State schema & Pydantic RouteDecision model
│   ├── router.py               # Async Orchestrator routing node with memory injection
│   ├── planner.py              # ReAct multi-step tool-use planner agent node
│   ├── research.py             # Async live web research agent node
│   ├── rag.py                  # Agentic document RAG agent node
│   ├── vision.py               # Multimodal Groq Vision agent node
│   ├── parallel.py             # Parallel agent fan-out & result merger node
│   ├── reflection.py           # Self-correction reflection critic node
│   ├── graph.py                # LangGraph workflow compiler
│   └── tools/                  # Executable Agent Tools
│       ├── calculator.py       # Safe math AST evaluation tool
│       ├── datetime_tool.py    # UTC system date/time tool
│       ├── memory_tool.py      # Long-term memory search & store tools
│       └── code_executor.py    # Sandboxed Python code execution tool
│
├── RAG/                        # Multimodal Agentic RAG Subsystem
│   ├── embeddings.py           # HuggingFace embeddings wrapper
│   ├── retriever.py            # Hybrid retrieval (FAISS + BM25 + Reciprocal Rank Fusion)
│   ├── manager.py              # Document loader (PDF, DOCX, TXT, OCR) & vector manager
│   └── query_engine.py         # Agentic query engine (HyDE, Sub-Query Decomposition, Rewriting)
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
│   └── s3_manager.py           # Amazon S3 document manager & presigned URL generator
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
├── tests/                      # Automated Pytest Suite (>80% Coverage Target)
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

## 🌟 Key Technical Capabilities

### 1. ⚡ Non-Blocking Async Execution & Token SSE Streaming
All LangGraph agent nodes are native `async def` routines using `ainvoke()`. The streaming endpoint (`POST /api/chat/stream`) utilizes `graph.astream_events()` to pipe real-time token chunks and route events directly to the client via Server-Sent Events.

### 2. 🧰 ReAct Multi-Step Tool-Use Planner
Equipped with `llm.bind_tools()` enabling the planner agent to reason, invoke tools, inspect observations, and formulate verified responses:
- **Calculator Tool**: Evaluates complex mathematical expressions safely using an AST evaluator.
- **System Datetime Tool**: Real-time UTC time, date, and calendar context.
- **Long-Term Memory Tool**: Searches and records user preferences across sessions.
- **Python Code Execution Sandbox**: Executes data scripts in an isolated subprocess with timeout protection.

### 3. 🧠 Agentic RAG with HyDE & Multi-Hop Decomposition
Goes beyond naive semantic search:
- **HyDE (Hypothetical Document Embeddings)**: Generates hypothetical response passages to search vector spaces more accurately.
- **Query Decomposition**: Deconstructs multi-hop research queries into targeted sub-queries.
- **Feedback-Driven Query Rewriting**: If the reflection node flags ungrounded output, the query engine rewrites search queries automatically.

### 4. 🔀 Concurrent Agent Fan-Out
Handles compound prompts (e.g., *"Summarize the uploaded financial report and fetch today's market news"*) by dispatching tasks to Research and RAG agents concurrently using `asyncio.gather()` and merging their outputs into a unified response.

### 5. 🛡️ Enterprise Security, Guardrails & GDPR Compliance
- **Cognito JWT & RBAC**: Authorization middleware validating tokens and enforcing `Admin`, `User`, or `ReadOnly` permissions.
- **Luhn Algorithm & PII Redaction**: Fast regex redacting enhanced with Luhn validation for credit cards to eliminate false positives.
- **ML LLM-Judge Injection Classifier**: An adversarial classification layer blocking instruction overrides and prompt injection.
- **Output Safety Guardrail v2**: Checks for toxic content, bias, and PII/API key leakage.
- **GDPR Data Erasure**: `DELETE /api/user/{user_id}/data` purges database records, chat histories, user memories, and vector index chunks.

---

## 📡 Complete REST API Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/chat` | Multi-agent execution & background fact distillation | Optional |
| `POST` | `/api/chat/stream` | Token-level Server-Sent Events (SSE) streaming | Optional |
| `POST` | `/api/ingest` | Upload document to S3, chunk, and index into RAG | Optional |
| `GET` | `/api/documents/{user_id}` | List user documents and chunks metadata | Optional |
| `DELETE` | `/api/documents/{user_id}` | Delete all user document chunks from RAG | Optional |
| `GET` | `/api/memories/{user_id}` | Fetch active long-term memories for user | Optional |
| `POST` | `/api/memories` | Manually insert a long-term memory fact | Optional |
| `DELETE` | `/api/user/{user_id}/data`| **GDPR Purge**: Erase all chat, memory, and RAG data | User / Admin |
| `GET` | `/api/admin/users` | List all registered user accounts and status | Admin |
| `GET` | `/api/health` | System health check, active model, and stats | None |

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.11+
- Groq API Key (Sign up at [console.groq.com](https://console.groq.com))

### 2. Environment Configuration
Clone the repository and set up your `.env`:

```bash
cp .env.example .env
```

Set your API keys:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
VISION_MODEL=llama-3.2-11b-vision-preview

# Optional AWS Cloud Integrations
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

## 💻 Running & Deployment

### Option A: One-Command Deployment Script (Easiest)
```bash
chmod +x deploy.sh
./deploy.sh
```

### Option B: Docker Compose (Production Ready)
```bash
docker-compose up -d --build
```
- Access **Web Workbench**: `http://localhost:8000`
- Access **Swagger API Docs**: `http://localhost:8000/docs`

### Option C: Native Python Server
```bash
python main.py --serve-api
```

### Option D: CLI Interactive Chat
```bash
python main.py
```

---

## 🧪 Automated Testing & Evaluation Harness

Run the full automated test suite with code coverage:

```bash
pytest tests/ --cov=. --cov-report=term-missing
```

Run the multi-agent regression benchmark harness:

```bash
python main.py --run-harness
```

---

## 📄 License

This project is licensed under the MIT License.