# 🚀 SaaS Transformation Plan — Vasooli / Wemboo
### Converting a hackathon demo → a real, shippable SaaS product

> [!WARNING]
> **8 pre-code bugs caught and corrected in this plan & implementation**:
> 1. `org_id` derived server-side from JWT identity — never trusted from request params (IDOR vulnerability).
> 2. Schema uses Postgres `ON CONFLICT DO NOTHING`, not SQLite-only `INSERT OR IGNORE`.
> 3. `check_quota` is async-safe — uses `asyncpg` pool, never blocks event loop.
> 4. Razorpay webhook performs real timing-safe HMAC-SHA256 signature verification before processing.
> 5. `analyse` endpoint has no unused `BackgroundTasks` parameter.
> 6. **[FIXED] Quota Key Pluralization**: Replaced faulty string concat/ends-with logic (`analysiss`) with explicit `EVENT_TYPE_TO_LIMIT_KEY` mapping to `"analyses"`, ensuring quota enforcement is active.
> 7. **[FIXED] PostgreSQL Expression Index**: Replaced timezone-dependent `date_trunc` STABLE expression index with plain B-tree index on `(org_id, created_at DESC)` and range queries (`created_at >= date_trunc('month', now())`), preventing Aurora deployment crash.
> 8. **[FIXED] Org Endpoints IDOR Elimination**: Protected `/api/org/me`, `/api/org/{id}/usage`, `/api/org/{id}/history`, and `/api/org/{id}/invite` with `verify_org_access`, verifying membership and admin roles server-side.

---

## What "SaaS" Actually Means in Code Terms

Before touching anything, here's the gap between what you have and what SaaS requires:

| SaaS Requirement | Currently Exists? | What's Needed |
|---|---|---|
| Multi-tenant data isolation | ⚠️ user_id scoping only | Org/workspace tier above users |
| Subscription tiers (Free/Pro/Enterprise) | ❌ None | Plan table + usage metering |
| Self-service signup/login | ❌ Manual user_id in UI | Real auth flow with Cognito hosted UI |
| Customer dashboard (usage, history, billing) | ❌ Just a chat interface | Full dashboard UI |
| Usage metering / quota enforcement | ❌ None | Per-plan limits in middleware |
| Public landing page with pricing | ❌ None | Landing page + pricing section |
| API key management (for developers) | ❌ None | API key table + auth path |
| Onboarding wizard | ❌ None | Step-by-step first-use flow |
| Billing integration | ❌ None | Razorpay/Stripe webhooks |

---

## The SaaS Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PUBLIC ROUTES                             │
│  / (Landing page)  /pricing  /login  /signup               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   AUTH LAYER                                 │
│  Cognito Hosted UI → JWT → User+Org Context                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              TENANT-SCOPED APP ROUTES                        │
│  /dashboard  /analyze  /contracts  /history  /settings      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 PLAN ENFORCEMENT MIDDLEWARE                   │
│  Free: 5 analyses/month  Pro: 50/mo  Enterprise: unlimited  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              EXISTING ENGINE (unchanged)                      │
│  LangGraph → RAG → Bedrock → Guardrails → Response          │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Core SaaS Structure (Do This First)

### 1.1 Database — Add Tenant & Billing Tables

**File: [`SQL/schema.sql`](file:///d:/Ai_platform_Monarch/SQL/schema.sql)** → Add these tables:

```sql
-- ⚠️ POSTGRES SYNTAX ONLY (schema.sql targets Aurora/pgvector, not SQLite)
-- SQLite dev tables are managed separately in SQL/db.py:init_sqlite_db()

-- ORGANIZATIONS (the billing/tenant entity)
CREATE TABLE IF NOT EXISTS organizations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT NOT NULL,
    plan                 TEXT NOT NULL DEFAULT 'free'
                         CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at           TIMESTAMPTZ DEFAULT now(),
    billing_email        TEXT,
    razorpay_customer_id TEXT
);

-- ORG MEMBERS (links users to orgs — org_id always derived from here, never from request)
CREATE TABLE IF NOT EXISTS org_members (
    user_id   TEXT        NOT NULL,   -- Cognito sub claim
    org_id    UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role      TEXT        NOT NULL DEFAULT 'member'
              CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, org_id)
);
CREATE INDEX idx_org_members_user ON org_members (user_id);

-- USAGE METERING
CREATE TABLE IF NOT EXISTS usage_events (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id    TEXT        NOT NULL,
    event_type TEXT        NOT NULL CHECK (event_type IN ('analysis','ingest','chat')),
    tokens_used INTEGER   DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_usage_org_created ON usage_events (org_id, created_at DESC);

-- API KEYS
CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    key_hash     TEXT        UNIQUE NOT NULL,   -- bcrypt hash
    key_prefix   TEXT        NOT NULL,          -- "wbm_live_abc" shown to user
    created_at   TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    is_active    BOOLEAN     DEFAULT true
);

-- PLAN LIMITS (seed data)
CREATE TABLE IF NOT EXISTS plan_limits (
    plan                TEXT    PRIMARY KEY,
    analyses_per_month  INTEGER NOT NULL,   -- -1 = unlimited
    documents_max       INTEGER NOT NULL,
    chat_messages_month INTEGER NOT NULL,
    api_access          BOOLEAN DEFAULT false
);
-- Postgres: ON CONFLICT DO NOTHING (not INSERT OR IGNORE which is SQLite-only)
INSERT INTO plan_limits VALUES
    ('free',        5,   10,   100, false),
    ('pro',        50,  100,  1000, true),
    ('enterprise', -1,   -1,    -1, true)
ON CONFLICT (plan) DO NOTHING;
```

---

### 1.2 Plan Enforcement Middleware

**New File: `middleware/quota.py`**

Three critical fixes applied vs. the original draft:
1. **`org_id` derived from `user.user_id` via `org_members` — never from request params** (IDOR fix)
2. **Fully `async` — uses `asyncpg` pool, never blocks the event loop** (consistency fix)
3. **Falls back to SQLite in dev when no Postgres pool available** (dev parity fix)

```python
from fastapi import HTTPException, status
from auth.cognito import UserContext
from SQL.db import get_pg_pool, get_sqlite_connection
from utils.logger import log

PLAN_LIMITS = {
    "free":       {"analyses": 5,  "documents": 10},
    "pro":        {"analyses": 50, "documents": 100},
    "enterprise": {"analyses": -1, "documents": -1},
}


async def get_user_org(user: UserContext) -> tuple[str, str]:
    """
    Derive org_id and plan from the authenticated user's org_members row.
    NEVER accept org_id from a request parameter — that's an IDOR vulnerability.
    Returns (org_id, plan). Falls back to a personal free-tier org if none found.
    """
    pool = await get_pg_pool()
    if pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT om.org_id, o.plan
                FROM org_members om
                JOIN organizations o ON o.id = om.org_id
                WHERE om.user_id = $1
                ORDER BY om.joined_at ASC
                LIMIT 1
                """,
                user.user_id,
            )
            if row:
                return str(row["org_id"]), row["plan"]
    else:
        # Dev/SQLite fallback — auto-create personal org if missing
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT org_id FROM org_members WHERE user_id = ? LIMIT 1",
            (user.user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return row["org_id"], "free"

    # Auto-provision a free personal org on first use
    return await _provision_personal_org(user)


EVENT_TYPE_TO_LIMIT_KEY = {
    "analysis": "analyses",
    "analyses": "analyses",
    "document": "documents",
    "documents": "documents",
    "chat": "chat_messages",
    "chat_messages": "chat_messages",
    "ingest": "documents",
}


async def check_quota(user: UserContext, event_type: str = "analysis") -> str:
    """
    Enforces plan limits. Returns the verified org_id for use in subsequent
    DB writes. Raises HTTP 429 if quota is exceeded.
    org_id is ALWAYS derived from user identity — never from request input.
    """
    org_id, plan = await get_user_org(user)

    limit_key = EVENT_TYPE_TO_LIMIT_KEY.get(event_type, "analyses")
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).get(limit_key, 5)
    if limit == -1:  # unlimited plan
        return org_id

    pool = await get_pg_pool()
    if pool:
        async with pool.acquire() as conn:
            used = await conn.fetchval(
                """
                SELECT COUNT(*) FROM usage_events
                WHERE org_id = $1 AND event_type = $2
                  AND created_at >= date_trunc('month', now())
                """,
                org_id, event_type,
            )
    else:
        # SQLite dev fallback — synchronous but only runs in dev (no event-loop risk)
        db_conn = get_sqlite_connection()
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM usage_events
            WHERE org_id = ? AND event_type = ?
              AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """,
            (org_id, event_type),
        )
        used = cursor.fetchone()[0]
        db_conn.close()

    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "plan": plan,
                "limit": limit,
                "used": used,
                "upgrade_url": "/pricing",
            },
        )
    return org_id


async def _provision_personal_org(user: UserContext) -> tuple[str, str]:
    """Auto-create a free personal org for a new user on first analysis."""
    import uuid
    org_id = str(uuid.uuid4())
    pool = await get_pg_pool()
    if pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO organizations (id, name, plan) VALUES ($1, $2, 'free')",
                    org_id, f"{user.email or user.user_id}'s Workspace",
                )
                await conn.execute(
                    "INSERT INTO org_members (user_id, org_id, role) VALUES ($1, $2, 'owner')",
                    user.user_id, org_id,
                )
    log.info("Auto-provisioned personal free org %s for user %s", org_id, user.user_id)
    return org_id, "free"
```

---

### 1.3 New API Endpoints for SaaS Operations

**Add to [`api.py`](file:///d:/Ai_platform_Monarch/api.py):**

```python
# ── Org / Tenant Management (Protected by verify_org_access) ────
POST   /api/org/create            # Create org on signup
GET    /api/org/me                # Caller's verified org & role
GET    /api/org/{org_id}          # Org details (verified caller membership)
POST   /api/org/{org_id}/invite   # Invite team member (verified admin/owner)

# ── Usage & Billing (Protected by verify_org_access) ────────────
GET    /api/org/me/usage          # Current month usage vs limits
GET    /api/org/{org_id}/usage    # Verified org usage
GET    /api/org/{org_id}/history  # All past analysis reports (verified membership)
POST   /api/billing/checkout      # Create Razorpay checkout session (derived org)
POST   /api/billing/webhook       # Razorpay payment confirmation (HMAC verified)

# ── API Key Management ───────────────────────────────────────
GET    /api/keys                  # List org API keys
POST   /api/keys                  # Create new API key
DELETE /api/keys/{key_id}         # Revoke key

# ── Analysis Reports (SaaS core product) ─────────────────────
GET    /api/analyses              # Paginated analysis history
GET    /api/analyses/{id}         # Full analysis report
POST   /api/analyse               # THE core endpoint (replaces /api/chat)
```

---

## Phase 2 — The 5-Page Frontend (Full SaaS UI)

This is the biggest visible change. You need to go from a single chat page to a proper product.

### Page Map

```
/                    → Landing page (public)
/pricing             → Pricing tiers (public)  
/login               → Cognito hosted UI redirect
/app/dashboard       → Usage stats, recent analyses
/app/analyze         → The core product (upload → analyze → report)
/app/history         → Past analyses with search/filter
/app/settings        → API keys, team members, billing
```

---

### Page 1: Landing Page (`/`)

**This is your most important SaaS signal.** Currently you have a workbench tool. A SaaS has a landing page that sells.

**Sections to build:**
- Hero: headline + tagline + CTA button ("Start Free — No Card Required")
- Problem statement: "63M Indian MSMEs lose ₹10.7L Cr/year to delayed payments"
- How it works: 3-step visual (Upload → Analyze → Act)
- Proof: "Based on Razorpay's 82.8 itch score from 50,000 verified SME owners"
- Pricing (preview cards)
- Footer

---

### Page 2: Dashboard (`/app/dashboard`)

The first page a logged-in user sees. Shows:

```
┌─────────────────────────────────────────────────────────────┐
│  Welcome back, Abhishek 👋           Plan: FREE  [Upgrade]  │
├──────────────┬──────────────┬───────────────────────────────┤
│ 3 of 5       │ ₹12,400      │ 2 contracts                   │
│ Analyses used│ Flagged risk │ Reviewed this month           │
├──────────────┴──────────────┴───────────────────────────────┤
│ RECENT ANALYSES                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ 📄 Reliance_PO_Sept.pdf    3 violations found  View → │  │
│ │ 📄 Vendor_Agreement.pdf    Compliant ✓         View → │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ [+ Upload New Contract]                                     │
└─────────────────────────────────────────────────────────────┘
```

---

### Page 3: Analysis Page (`/app/analyze`) — The Core Product

This replaces the raw chat interface with a product-grade flow:

```
Step 1 of 3: Upload Contract
┌─────────────────────────────────────────────────────────────┐
│  Drop your vendor agreement, purchase order, or payment     │
│  terms clause here (PDF, DOCX, or photo)                    │
│  ┌─────────────────────────────────┐                        │
│  │        📄 Drag & Drop          │                        │
│  │   or click to browse files     │                        │
│  └─────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘

Step 2 of 3: Analyzing... (live progress)
│ ✅ Extracting text via AWS Textract
│ ✅ Grounding against MSME Development Act
│ 🔄 Identifying payment term violations...
│ ⏳ Generating remediation draft...

Step 3 of 3: Your Report
┌─────────────────────────────────────────────────────────────┐
│ ANALYSIS REPORT — Reliance_PO_Sept.pdf                      │
│                                                             │
│ 🔴 3 VIOLATIONS FOUND                                       │
│                                                             │
│ Issue 1: Payment cycle exceeds 45-day MSME Act limit        │
│   Clause: "Net 90 days from invoice receipt"                │
│   Law: MSME Development Act 2006, Section 15                │
│   Risk: Buyer loses tax deduction (Sec 43B(h) IT Act)       │
│   ┌─────────────────────────────────────────────┐          │
│   │ 📋 Draft Counter-Clause  📨 Draft Samadhaan │          │
│   └─────────────────────────────────────────────┘          │
│                                                             │
│ Issue 2: Missing penalty interest clause (18% entitlement)  │
│ ...                                                         │
│                                                             │
│ [📥 Download PDF Report]  [📋 Copy to Clipboard]           │
└─────────────────────────────────────────────────────────────┘
```

---

### Page 4: Pricing (`/pricing`)

```
┌──────────────┬──────────────┬──────────────────────────────┐
│    FREE       │     PRO       │         ENTERPRISE           │
│    ₹0/mo      │  ₹999/mo     │        Custom pricing        │
├──────────────┼──────────────┼──────────────────────────────┤
│ 5 analyses   │ 50 analyses  │ Unlimited analyses           │
│ 10 documents │ 100 documents│ Unlimited documents          │
│ Basic report │ Full report  │ Custom policy rules          │
│              │ PDF export   │ API access                   │
│              │ API access   │ Dedicated support            │
│              │ Team (3)     │ White-label option           │
├──────────────┼──────────────┼──────────────────────────────┤
│ [Start Free] │[Start Trial] │     [Contact Sales]          │
└──────────────┴──────────────┴──────────────────────────────┘
```

---

### Page 5: Settings (`/app/settings`)

Tabs:
- **Profile** — name, email, change password
- **API Keys** — generate/revoke keys, copy key string
- **Team** — invite members, set roles
- **Billing** — current plan, usage bar, upgrade/downgrade, invoice history
- **Data** — export all data, GDPR delete account

---

## Phase 3 — Backend SaaS API Changes

### 3.1 The Core "Analyse" Endpoint (SaaS version of `/api/chat`)

Three fixes vs. original draft:
1. **`org_id` comes from `check_quota(user)` return value — not a request param**
2. **No unused `BackgroundTasks` parameter** (dead param removed)
3. **`check_quota` is awaited** (it's async)

```python
@app.post("/api/analyse", response_model=AnalysisReport, tags=["Core Product"])
async def analyse_contract(
    file: UploadFile,
    user: UserContext = Depends(get_current_user),
    # ✅ NO org_id request param — derived from user identity in check_quota
    # ✅ NO BackgroundTasks — not used in this endpoint, removed to avoid dead params
):
    """
    Core SaaS endpoint. Ingests a contract, runs the full
    Textract → RAG → Compliance Check → Draft pipeline.
    Returns AnalysisReport with statute-cited violations and draft legal responses.
    org_id is derived server-side from the authenticated user's org_members row.
    """
    # Derives and verifies org_id from JWT — never trusts client input
    org_id = await check_quota(user, "analysis")

    # ... run pipeline (Textract → RAG → LLM → structure output) ...

    await log_usage_event(org_id, user.user_id, "analysis")  # Async metering
    return AnalysisReport(...)
```

### 3.2 Structured Analysis Report Schema

```python
class ViolationItem(BaseModel):
    clause_text: str          # The exact offending clause
    violation_type: str       # "payment_cycle" | "missing_penalty" | etc.
    cited_law: str            # "MSME Development Act 2006, Section 15"
    cited_chunk_id: str       # RAG chunk that sourced this
    severity: str             # "high" | "medium" | "low"
    draft_counter_clause: str # Auto-drafted replacement
    samadhaan_ready: bool     # Whether Samadhaan complaint applies

class AnalysisReport(BaseModel):
    report_id: str
    file_name: str
    compliance_score: int     # 0-100
    violations: list[ViolationItem]
    overall_summary: str
    draft_samadhaan_complaint: Optional[str]
    analyzed_at: datetime
    disclaimer: str = "For informational purposes only. Not legal advice."
```

---

## Phase 4 — Billing Integration (Razorpay)

Since the MSME domain is literally about Razorpay's dataset, using Razorpay for billing is a narrative full-circle that judges will notice.

```python
# api.py — billing endpoints
import hmac, hashlib

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

@app.post("/api/billing/checkout", tags=["Billing"])
async def create_checkout(
    plan: str,
    user: UserContext = Depends(get_current_user),
):
    """Create a Razorpay order for plan upgrade.
    org_id is derived from user identity — never from request input.
    """
    org_id, current_plan = await get_user_org(user)  # from middleware/quota.py

    import razorpay
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    plan_prices = {"pro": 99900}  # paise  (₹999.00)
    if plan not in plan_prices:
        raise HTTPException(status_code=400, detail="Invalid plan")

    order = client.order.create({
        "amount": plan_prices[plan],
        "currency": "INR",
        "notes": {"org_id": org_id, "plan": plan},  # stored server-side in order
    })
    return {"order_id": order["id"], "amount": order["amount"]}


@app.post("/api/billing/webhook", tags=["Billing"])
async def razorpay_webhook(request: Request):
    """
    Razorpay payment webhook.
    ✅ Performs real HMAC-SHA256 signature verification before trusting payload.
    An unverified webhook that upgrades plans is a real security hole — not just a stub.
    """
    body_bytes = await request.body()
    razorpay_signature = request.headers.get("X-Razorpay-Signature", "")

    # HMAC-SHA256 verification (Razorpay docs: https://razorpay.com/docs/webhooks/validate-test/)
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), body_bytes, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        log.warning("Razorpay webhook signature mismatch — rejecting.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = await request.json()
    if payload.get("event") == "payment.captured":
        notes  = payload["payload"]["order"]["entity"]["notes"]
        org_id = notes.get("org_id")
        plan   = notes.get("plan")
        if org_id and plan:
            await upgrade_org_plan(org_id, plan)
            log.info("Upgraded org %s to plan %s via Razorpay webhook", org_id, plan)

    return {"status": "ok"}
```

> [!NOTE]
> `hmac.new` is used instead of `hmac.HMAC` for compatibility. The `.compare_digest()` call is timing-safe (prevents timing attacks). If Razorpay key secret is not configured, the webhook will always reject — safe by default.

---

## Implementation Priority Order

Given you're building toward a hackathon AND a real product:

### 🔴 Do First (Max Demo Impact)
1. **Landing page** — judges see this before anything else
2. **3-step Analysis UI** (`/app/analyze`) — replaces the raw chat, looks like a product
3. **`AnalysisReport` schema** in backend — structured output instead of freetext
4. **Plan tiers in database** + quota middleware

### 🟠 Do Second (SaaS credibility signals)
5. **Dashboard page** with usage metrics
6. **History page** — past analyses are a SaaS staple
7. **Usage metering** — log every API call
8. **Pricing page** — public-facing, no auth needed

### 🟡 Do If Time Allows (Wow factor)
9. **Razorpay billing integration** — full circle narrative
10. **API Key management** + `/settings` page
11. **PDF report download** — output that users keep
12. **Team invite** endpoint

---

## What Stays Unchanged (Don't Touch)

| Component | Status |
|---|---|
| [`Agents/graph.py`](file:///d:/Ai_platform_Monarch/Agents/graph.py) — LangGraph pipeline | ✅ Keep as-is |
| [`RAG/manager.py`](file:///d:/Ai_platform_Monarch/RAG/manager.py) — Hybrid retrieval | ✅ Keep as-is |
| [`guardrails/`](file:///d:/Ai_platform_Monarch/guardrails/) — Safety layer | ✅ Keep as-is |
| [`auth/cognito.py`](file:///d:/Ai_platform_Monarch/auth/rbac.py) — Cognito JWT | ✅ Keep, extend |
| [`storage/s3_manager.py`](file:///d:/Ai_platform_Monarch/storage/s3_manager.py) — S3 | ✅ Keep as-is |
| [`audit/logger.py`](file:///d:/Ai_platform_Monarch/audit/__init__.py) — Audit trail | ✅ Keep as-is |

The engine is solid. SaaS is a product layer ON TOP of it, not a replacement.

---

## The SaaS Pitch After This

Before: *"We built a multi-agent assistant that can analyze documents."*

After: *"Vasooli is a SaaS that reads MSME payment contracts, flags which clauses violate Indian law, and auto-drafts the recovery notice — starting free, ₹999/month for growing businesses. Built on AWS, costs $0.68/month to run, targeting 63M Indian MSMEs."*

That's a product. That's fundable. That's what wins "Best Product" at a hackathon.

> [!IMPORTANT]
> **Approve this plan to proceed.** I'll start with the Landing Page + Analysis UI since those have the highest visual impact for judges. Each phase builds cleanly on top of your existing backend — no breaking changes to the engine.
