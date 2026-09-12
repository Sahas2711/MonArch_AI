# 🚀 Vasooli / Wemboo — AI Payment Compliance & Recovery SaaS for 63M Indian MSMEs

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![Cedar Policy Engine](https://img.shields.io/badge/Cedar-Policy_Engine-green.svg)](https://www.cedarpolicy.com/)
[![AWS Cloud](https://img.shields.io/badge/AWS-Bedrock_|_Textract_|_Step_Functions_|_S3_|_Cognito_|_DynamoDB-ff9900.svg?style=flat&logo=amazon-aws)](https://aws.amazon.com/)
[![Strands Agents](https://img.shields.io/badge/Strands-Agents_SDK-orange.svg)](https://aws.amazon.com/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Billing_&_Webhooks-0C2340.svg?style=flat&logo=razorpay)](https://razorpay.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **"63 Million Indian MSMEs lose ₹10.7 Lakh Crore every year to delayed payments."**  
> **Vasooli / Wemboo** is an enterprise-grade multi-tenant SaaS application powered by the **Cedar Policy Engine**, **AWS Bedrock**, **Amazon Textract**, and **Strands Agents SDK**. It audits buyer agreements, flags illegal credit clauses under the **MSME Development Act 2006 (Sections 15 & 16)**, computes **Section 43B(h)** Income Tax disallowances, and auto-drafts legal notices & **MSME Samadhaan Form 1** arbitration complaints in seconds.

---

## 🏗 SaaS System Architecture & Pipeline

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
│   Monthly Quota Tracking  •  Async Usage Event Metering (DynamoDB / PG)  │
└──────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌──────────────────────────────────────────────────────────────────────────┐
│              CEDAR FAIRNESS ENGINE & STRANDS ACTION AGENT                │
│   • Amazon Textract: Structured Clause & Expense Extraction              │
│   • Cedar Policy Packs: Domain policy rules (rules.cedar & schema)       │
│   • Fairness Node: Evaluates clauses against MSME statutory rules        │
│   • Strands Action Agent: Drafts Form 1 Samadhaan complaints             │
│   • Bedrock Guardrails: Legal hallucination & safety verification        │
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

## 🛡️ Cedar Policy Engine & MSME Fairness Engine

Vasooli features a domain-swappable policy evaluation engine powered by the **Cedar Policy Engine**:

- **Domain Policy Packs** (`policy_packs/msme_payment_terms/`):
  - `schema.cedarschema`: Entity definitions (`Clause`, `Evaluation`, `flag` action).
  - `rules.cedar`: Codified statutory rule checks (45-day payment cap, mandatory compound interest, unilateral cancellation).
  - `loader.py`: `PolicyPack.load(name)` interface allowing instant domain swapping (rental, tax, procurement contracts) without modifying agent node code.
- **Fairness Agent Node** (`Agents/fairness.py`): Runs Cedar policy evaluation over extracted clause entities, emitting structured violation items.

---

## ⚖️ Indian Statutory Legal Protections Enforced

| Indian Statute | Legal Mandate | How Vasooli Enforces It |
|---|---|---|
| **MSME Act 2006, Section 15** | Payment period agreed in writing **cannot exceed 45 days** (15 days if no agreement). | Cedar rule flags 60/90/120-day clauses as *void ab initio*; auto-drafts compliant 45-day substitute clauses. |
| **MSME Act 2006, Section 16** | Mandatory compound interest with monthly rests at **three times (3x) the RBI Bank Rate** on delayed dues. | Computes exact compound interest from the due date and inserts statutory interest claims into demand notices. |
| **Income Tax Act, Section 43B(h)** | Any sum payable to Micro/Small enterprise remaining unpaid beyond Section 15 limits is **disallowed as a business deduction** for the buyer. | Generates tax disallowance notices showing the buyer their increased corporate tax liability if they fail to pay on time. |
| **MSME Act 2006, Section 18** | Direct right of reference to the Micro and Small Enterprise Facilitation Council (**MSEFC / Samadhaan**). | Strands Action Agent drafts formatted **Form 1 Legal Complaint Applications** ready for portal filing. |

---

## ☁️ AWS Cloud Native Integrations

- **Amazon Bedrock**: Primary LLM path using `ChatBedrockConverse` (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`) with automatic Groq fallback.
- **Amazon Textract**: Uses `AnalyzeDocument` (FORMS & TABLES) and `AnalyzeExpense` to extract clause fields from contracts and invoices (`utils/textract.py`).
- **AWS Step Functions & EventBridge**: S3 document upload triggers EventBridge rule invoking the Step Functions orchestration state machine (`infra/step_functions.json`).
- **Amazon DynamoDB**: Single-table design with PK `ORG#<id>` and SK `USAGE#<timestamp>` for serverless multi-tenant meter tracking (`SQL/dynamodb.py`).
- **Amazon Bedrock Guardrails**: Secondary output safety layer evaluating hallucination and PII leakage on legal complaint drafts (`guardrails/bedrock_guard.py`).

---

## 🌟 5-Page SaaS Product Experience

```
/                → Public Landing Page (High-converting copy, crisis stats, live audit widget)
/pricing         → Public Pricing Tiers (Free ₹0, Pro ₹999/mo, Enterprise ₹4,999/mo)
/app             → Customer Dashboard (Live quota meter, recent audit reports, quick actions)
/app#analyze     → 3-Step Audit Wizard (Upload / Paste clause → Cedar Policy Evaluation → Legal Report)
/app#history     → Audit Repository (Searchable, filterable history of audited contracts)
/app#settings    → Org Settings (API Key generation, Razorpay upgrade modal, tenant profile)
/workbench       → Developer Multi-Agent Workbench (Internal tool for debugging RAG & agents)
```

---

## 💳 SaaS Subscription Tiers & Billing

| Feature | Free Tier | Pro Plan (₹999/mo) | Enterprise (₹4,999/mo) |
|---|:---:|:---:|:---:|
| **Monthly Contract Audits** | 5 / month | **50 / month** | **Unlimited** |
| **Cedar Policy Engine Check** | ✓ Included | ✓ Included | ✓ Included |
| **Sec 15 45-Day Violation Check** | ✓ Included | ✓ Included | ✓ Included |
| **Sec 16 3x RBI Interest Calculator**| ✓ Included | ✓ Included | ✓ Included |
| **Sec 43B(h) Tax Disallowance Alert**| Basic | ✓ Full Computation | ✓ Custom Corporate Tax Report |
| **Strands MSME Samadhaan Drafter** | Text Only | ✓ PDF Download | ✓ Batch Dispute Filing |
| **B2B Developer API Access** | ✕ | ✓ Included (1 Key) | ✓ Unlimited Keys + Webhooks |
| **Tally Prime / ERP Connector** | ✕ | ✕ | ✓ Direct Connector |
| **Payment & Billing Gateway** | Free | **Razorpay INR Auto-Renew** | **Razorpay / Invoice** |

---

## 📡 Complete REST API Reference

### Core Compliance & SaaS Endpoints

| Method | Endpoint | Description | Auth Scoped |
|---|---|---|:---:|
| `POST` | `/api/analyse` | **Core SaaS**: Ingests contract clause/file, runs Cedar statutory compliance check, returns `AnalysisReport` | Verified Org |
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
| `POST` | `/api/chat` | Multi-agent execution with LangGraph, Cedar, and memory distillation |
| `POST` | `/api/chat/stream` | Token-level Server-Sent Events (SSE) streaming output |
| `POST` | `/api/ingest` | Upload document to S3, chunk, and index into FAISS RAG vector store |
| `GET` | `/api/documents/{user_id}` | List ingested knowledge documents and metadata |
| `DELETE`| `/api/documents/{user_id}` | Purge user document chunks from RAG vector index |
| `GET` | `/api/memories/{user_id}` | Fetch active long-term distilled user memories |
| `POST` | `/api/memories` | Manually insert long-term user memory fact |
| `DELETE`| `/api/user/{user_id}/data`| **GDPR Erasure**: Purge all chat, memory, and RAG data |
| `GET` | `/api/health` | System health, model readiness, and LangSmith state |

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.11+
- AWS Credentials (Bedrock / Textract) or Groq API Key

### 2. Environment Configuration
Clone the repository and configure your `.env`:

```bash
cp .env.example .env
```

```env
# LLM & AWS Configuration
USE_BEDROCK=true
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# Fallback Groq Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

# Razorpay Payments Configuration
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret_key

# Storage & Database (DynamoDB / PostgreSQL / SQLite)
DATABASE_URL=sqlite:///monarch.db
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

Run the full automated test suite:

```bash
pytest tests/ -v --asyncio-mode=auto
```

Tests verify:
- ✅ **Cedar Policy Engine**: Section 15 (45-day cap), Section 16 (3x RBI interest), unilateral cancellation, and false-positive checks (`test_fairness_agent.py`)
- ✅ **Strands Action Agent**: Form 1 Samadhaan complaint drafting and empty violation handling (`test_action_agent.py`)
- ✅ **SaaS Compliance & Quotas**: Monthly quota enforcement (HTTP 429), tenant isolation, and IDOR-safe server-side org derivation (`test_saas.py`)
- ✅ **API Keys & Webhooks**: B2B key lifecycle and Razorpay HMAC-SHA256 signature verification (`test_api.py`)

---

## 📄 License

This project is licensed under the MIT License.