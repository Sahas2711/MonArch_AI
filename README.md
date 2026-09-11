# 🚀 Vasooli / Wemboo — AI Payment Compliance & Recovery SaaS for 63M Indian MSMEs

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![AWS Cloud](https://img.shields.io/badge/AWS-Bedrock_|_Textract_|_S3_|_Cognito-ff9900.svg?style=flat&logo=amazon-aws)](https://aws.amazon.com/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Billing_&_Webhooks-0C2340.svg?style=flat&logo=razorpay)](https://razorpay.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Multi--Tenant_Aurora-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **"63 Million Indian MSMEs lose ₹10.7 Lakh Crore every year to delayed payments."**  
> **Vasooli / Wemboo** is an enterprise-grade multi-tenant SaaS application that audits buyer agreements, flags illegal 90-day credit clauses under the **MSME Development Act 2006 (Sections 15 & 16)**, computes **Section 43B(h)** Income Tax disallowances, and auto-drafts legal notices & **MSME Samadhaan Form 1** arbitration complaints in seconds.

---

## 🏗 SaaS System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             PUBLIC FRONTEND                              │
│   / (Landing Page)     /pricing (SaaS Tiers)     /workbench (Dev Tool)   │
└──────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                       SECURITY & TENANT LAYER                            │
│   Amazon Cognito JWT / UserContext ──> Server-Side Org Derivation (IDOR-Safe)│
└──────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                   PLAN ENFORCEMENT MIDDLEWARE                            │
│   Free (5 audits/mo)  │  Pro (50 audits/mo)  │  Enterprise (Unlimited)   │
│   Monthly Quota Tracking  •  Async Usage Event Metering                  │
└──────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    CORE SAAS PRODUCT & RECOVERY ENGINE                   │
│   POST /api/analyse:                                                     │
│   • MSME Act Sec 15 (Mandatory 45-day credit cap enforcement)            │
│   • MSME Act Sec 16 (Compound interest @ 3x RBI Bank Rate calculation)   │
│   • Income Tax Sec 43B(h) (Buyer expense disallowance leverage)          │
│   • Auto-Draft Form 1 (MSEFC Samadhaan dispute application)              │
│   • Substitute Counter-Clause generation                                 │
└──────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                   INTELLIGENCE ENGINE (LangGraph + RAG)                  │
│   AWS Bedrock / Groq LLM  •  Hybrid FAISS/BM25  •  Multimodal Vision     │
└──────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                      BILLING & DEVELOPER PLATFORM                        │
│   • Razorpay Order Checkout (POST /api/billing/checkout)                 │
│   • Timing-Safe HMAC-SHA256 Webhooks (POST /api/billing/webhook)         │
│   • B2B API Key Management (GET/POST/DELETE /api/keys) for Tally & ERPs  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## ⚖️ Indian Statutory Legal Protections Enforced

| Indian Statute | Legal Mandate | How Vasooli Enforces It |
|---|---|---|
| **MSME Act 2006, Section 15** | Payment period agreed in writing **cannot exceed 45 days** (15 days if no agreement). | Flags 60/90/120-day clauses as *void ab initio*; auto-drafts compliant 45-day substitute clauses. |
| **MSME Act 2006, Section 16** | Mandatory compound interest with monthly rests at **three times (3x) the RBI Bank Rate** on delayed dues. Overrides any contract clause. | Computes exact compound interest from the due date and inserts statutory interest claims into demand notices. |
| **Income Tax Act, Section 43B(h)** | Any sum payable to Micro/Small enterprise remaining unpaid beyond Section 15 limits is **disallowed as a business deduction** for the buyer. | Generates tax disallowance notices showing the buyer their increased corporate tax liability if they fail to pay on time. |
| **MSME Act 2006, Section 18** | Direct right of reference to the Micro and Small Enterprise Facilitation Council (**MSEFC / Samadhaan**). | One-click generation of formatted **Form 1 Legal Complaint Applications** ready for portal filing. |

---

## 🌟 5-Page SaaS Product Experience

```
/                → Public Landing Page (High-converting copy, crisis stats, live audit widget)
/pricing         → Public Pricing Tiers (Free ₹0, Pro ₹999/mo, Enterprise ₹4,999/mo)
/app             → Customer Dashboard (Live quota meter, recent audit reports, quick actions)
/app#analyze     → 3-Step Audit Wizard (Upload / Paste clause → Bedrock Reasoning → Legal Report)
/app#history     → Audit Repository (Searchable, filterable history of audited contracts)
/app#settings    → Org Settings (API Key generation, Razorpay upgrade modal, tenant profile)
/workbench       → Developer Multi-Agent Workbench (Internal tool for debugging RAG & agents)
```

---

## 💳 SaaS Subscription Tiers & Billing

| Feature | Free Tier | Pro Plan (₹999/mo) | Enterprise (₹4,999/mo) |
|---|:---:|:---:|:---:|
| **Monthly Contract Audits** | 5 / month | **50 / month** | **Unlimited** |
| **Sec 15 45-Day Violation Check** | ✓ Included | ✓ Included | ✓ Included |
| **Sec 16 3x RBI Interest Calculator**| ✓ Included | ✓ Included | ✓ Included |
| **Sec 43B(h) Tax Disallowance Alert**| Basic | ✓ Full Computation | ✓ Custom Corporate Tax Report |
| **MSME Samadhaan Form 1 Drafter** | Text Only | ✓ PDF Download | ✓ Batch Dispute Filing |
| **B2B Developer API Access** | ✕ | ✓ Included (1 Key) | ✓ Unlimited Keys + Webhooks |
| **Tally Prime / ERP Connector** | ✕ | ✕ | ✓ Direct Connector |
| **Payment & Billing Gateway** | Free | **Razorpay INR Auto-Renew** | **Razorpay / Invoice** |

---

## 📡 Complete REST API Reference

### Core Compliance & SaaS Endpoints

| Method | Endpoint | Description | Auth Scoped |
|---|---|---|:---:|
| `POST` | `/api/analyse` | **Core SaaS**: Ingests contract clause/file, runs statutory compliance check, returns `AnalysisReport` | Verified Org |
| `GET` | `/api/analyses` | List all historical compliance audit reports for user's organization | Verified Org |
| `GET` | `/api/analyses/{id}` | Retrieve full structured analysis report by report ID | Verified Org |
| `POST` | `/api/org/create` | Create a new tenant organization / workspace | User |
| `GET` | `/api/org/{id}` | Retrieve organization profile, tier, and member details | Verified Org |
| `GET` | `/api/org/{id}/usage` | Current month usage versus plan quota limits | Verified Org |
| `POST` | `/api/org/{id}/invite` | Invite team members to organization with RBAC role | Admin |
| `POST` | `/api/billing/checkout`| Initiate Razorpay order session for Pro/Enterprise plan upgrades | Verified Org |
| `POST` | `/api/billing/webhook` | **Razorpay Webhook**: HMAC-SHA256 signature verification & plan upgrade | Gateway Verified |
| `GET` | `/api/keys` | List active B2B Developer API keys for ERP/Tally integration | Verified Org |
| `POST` | `/api/keys` | Generate new SHA-256 hashed `wm_live_...` API key | Verified Org |
| `DELETE` | `/api/keys/{id}` | Revoke an active API key | Verified Org |

### Multi-Agent & RAG Workbench Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Multi-agent execution with LangGraph and long-term memory distillation |
| `POST` | `/api/chat/stream` | Token-level Server-Sent Events (SSE) streaming output |
| `POST` | `/api/ingest` | Upload document to S3, chunk, and index into FAISS RAG vector store |
| `GET` | `/api/documents/{user_id}` | List ingested knowledge documents and metadata |
| `DELETE`| `/api/documents/{user_id}` | Purge user document chunks from RAG vector index |
| `GET` | `/api/memories/{user_id}` | Fetch active long-term distilled user memories |
| `POST` | `/api/memories` | Manually insert long-term user memory fact |
| `DELETE`| `/api/user/{user_id}/data`| **GDPR Erasure**: Purge all chat, memory, and RAG data |
| `GET` | `/api/health` | System health, model readiness, and LangSmith state |

---

## 🗄 Database Schema (PostgreSQL + SQLite Parity)

```sql
-- PostgreSQL Schema (SQL/schema.sql) / SQLite Dev (SQL/db.py)

-- Organizations (Tenant & Billing Entity)
CREATE TABLE organizations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT NOT NULL,
    plan                 TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    monthly_quota        INTEGER NOT NULL DEFAULT 5,
    current_usage        INTEGER NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ DEFAULT now(),
    billing_email        TEXT,
    razorpay_customer_id TEXT
);

-- Organization Members (JWT Sub -> Org mapping; IDOR-safe)
CREATE TABLE org_members (
    user_id   TEXT NOT NULL,
    org_id    UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role      TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, org_id)
);

-- Usage Events Metering
CREATE TABLE usage_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    event_type  TEXT NOT NULL CHECK (event_type IN ('analysis','ingest','chat')),
    tokens_used INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Developer B2B API Keys
CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    key_hash     TEXT UNIQUE NOT NULL,
    key_prefix   TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    is_active    BOOLEAN DEFAULT true
);

-- Analysis History Reports
CREATE TABLE analyses_history (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id          TEXT NOT NULL,
    buyer_name       TEXT NOT NULL,
    file_name        TEXT,
    compliance_score INTEGER NOT NULL,
    violations_count INTEGER NOT NULL DEFAULT 0,
    report_data      JSONB NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT now()
);
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.11+
- Groq API Key or AWS Bedrock Access

### 2. Environment Configuration
Clone the repository and configure your `.env`:

```bash
cp .env.example .env
```

```env
# LLM & Reasoning Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

# Razorpay Payments Configuration
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret_key

# Database (PostgreSQL in Production, SQLite in Dev)
DATABASE_URL=sqlite:///monarch.db

# Optional AWS Services
AWS_REGION=us-east-1
S3_DOCUMENTS_BUCKET=monarch-docs-storage
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Running the Application

### Option A: Production Web Server
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
- 🌐 **Landing Page**: `http://localhost:8000/`
- 💳 **Pricing Page**: `http://localhost:8000/pricing`
- 📱 **SaaS Application**: `http://localhost:8000/app`
- 🛠️ **Developer Workbench**: `http://localhost:8000/workbench`
- 📖 **Interactive Swagger Docs**: `http://localhost:8000/docs`

### Option B: Docker Compose
```bash
docker-compose up -d --build
```

---

## 🧪 Automated Testing

Run the full automated test suite including the SaaS multi-tenant compliance suite:

```bash
pytest tests/ -v
```

Tests verify:
- ✅ SQLite and PostgreSQL schema initialization
- ✅ Section 15 (45-day cap) and Section 16 (3x RBI interest) violation detection
- ✅ Pre-drafted MSME Samadhaan dispute notice generation
- ✅ Monthly quota enforcement (HTTP 429 when quota exceeded)
- ✅ Tenant isolation and IDOR-safe server-side org derivation
- ✅ B2B Developer API key lifecycle (create, list, revoke)
- ✅ Razorpay webhook timing-safe HMAC-SHA256 signature verification

---

## 📄 License

This project is licensed under the MIT License.