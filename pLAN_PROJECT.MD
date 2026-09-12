# Vasooli (Monarch/Wemboo fork) — Implementation Spec
### For use with an AI code editor (Claude Code / Cursor). Paste sections as tasks, in order.

---

## Ground rules for the AI code editor

- Do not modify `Agents/graph.py`, `RAG/manager.py`, `RAG/retriever.py`, `guardrails/`, `storage/s3_manager.py`, or `audit/logger.py` except where a task below explicitly says to.
- Every new agent node must follow the existing node signature pattern already used in `Agents/rag.py` / `Agents/research.py` (async function, takes and returns the shared `state` object defined in `Agents/state.py`).
- Every new route must be wired through `RouteSwitch` in `Agents/router.py`, not called directly from `api.py`.
- No blocking (synchronous, network, or file I/O) calls inside any `async def` — wrap with `anyio.to_thread.run_sync` if a library only offers a sync client.
- Every new endpoint must derive `org_id`/`user_id` from the authenticated JWT context (`Depends(get_current_user)`), never from a request body/path/query param.

---

## Task 1 — Add Cedar as the fairness policy engine

**Goal:** a new `fairness.py` agent node that evaluates extracted contract clauses against codified MSME-law rules using Cedar, and returns structured, cited violations.

### 1.1 Install and scaffold

```bash
pip install cedarpy  # Python bindings for Cedar policy evaluation
```

Create directory:
```
policy_packs/
  msme_payment_terms/
    rules.cedar
    schema.cedarschema
    README.md
```

### 1.2 Write the Cedar schema (`policy_packs/msme_payment_terms/schema.cedarschema`)

```
entity Clause {
  paymentDays: Long,
  hasPenaltyInterestClause: Bool,
  hasUnilateralCancellation: Bool,
  buyerType: String,   // "large_enterprise" | "msme"
};

entity Evaluation {};

action "flag" appliesTo {
  principal: [Evaluation],
  resource: [Clause]
};
```

### 1.3 Write the policy rules (`policy_packs/msme_payment_terms/rules.cedar`)

```
// Rule 1: payment cycle exceeding the MSME Act 45-day limit
permit (
  principal,
  action == Action::"flag",
  resource
) when {
  resource.paymentDays > 45
};

// Rule 2: missing statutory penalty-interest entitlement
permit (
  principal,
  action == Action::"flag",
  resource
) when {
  resource.hasPenaltyInterestClause == false
};

// Rule 3: one-sided cancellation terms
permit (
  principal,
  action == Action::"flag",
  resource
) when {
  resource.hasUnilateralCancellation == true
};
```

Each `permit` that evaluates true = one violation. Keep one rule per file section so you can label *which* rule fired in the output (needed for the `cited_law` field below).

### 1.4 Build the Policy Pack loader interface

**New file: `policy_packs/loader.py`**

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PolicyPack:
    name: str
    policy_dir: Path
    corpus_dir: Path          # legal reference text for RAG grounding
    action_template: str      # prompt template for the action/drafting agent

    @classmethod
    def load(cls, name: str) -> "PolicyPack":
        base = Path("policy_packs") / name
        return cls(
            name=name,
            policy_dir=base,
            corpus_dir=base / "corpus",
            action_template=(base / "action_template.txt").read_text(),
        )
```

This is what makes the fairness engine swappable per domain later (rental agreements, tax docs, etc.) without touching node code — only add a new folder.

### 1.5 Build the fairness agent node

**New file: `Agents/fairness.py`**

```python
from cedarpy import AuthzResult, is_authorized  # verify exact API against cedarpy docs
from policy_packs.loader import PolicyPack
from Agents.state import AgentState
from utils.logger import log

async def fairness_node(state: AgentState) -> AgentState:
    """
    Evaluates extracted clause fields against the active Policy Pack's
    Cedar rules. Runs once per extracted clause. Cedar evaluation is
    synchronous/CPU-bound and fast (no network I/O) — safe to call
    directly inside async def without a thread-pool wrapper, but
    confirm this against cedarpy's actual implementation before shipping.
    """
    pack = PolicyPack.load(state.active_policy_pack or "msme_payment_terms")
    violations = []

    for clause in state.extracted_clauses:
        entity = {
            "paymentDays": clause.payment_days,
            "hasPenaltyInterestClause": clause.has_penalty_interest,
            "hasUnilateralCancellation": clause.has_unilateral_cancellation,
            "buyerType": clause.buyer_type,
        }
        result: AuthzResult = is_authorized(
            policy_dir=pack.policy_dir, action="flag", resource=entity
        )
        if result.decision == "Allow":  # a rule fired → flag this clause
            violations.append({
                "clause_text": clause.raw_text,
                "matched_rules": result.reasons,  # which rule(s) fired
                "clause_id": clause.id,
            })

    state.fairness_violations = violations
    log.info("Fairness node flagged %d violations", len(violations))
    return state
```

**Wire into the graph:** in `Agents/router.py`, add a route in `RouteSwitch` for document-type `"contract"` → `fairness_node`, following the existing pattern used for `RAGNode`/`VisionNode`. Do not change how `RouteSwitch` itself decides routes — only add the new branch.

### 1.6 Tests (required before merging)

**New file: `tests/test_fairness_agent.py`** — one test per Cedar rule:
```python
async def test_flags_payment_cycle_over_45_days(): ...
async def test_flags_missing_penalty_clause(): ...
async def test_flags_unilateral_cancellation(): ...
async def test_does_not_flag_compliant_clause(): ...  # false-positive check
```

---

## Task 2 — Add Strands Agents SDK for one node (not a full rewrite)

**Goal:** add genuine "built with AWS's own agent framework" credit without destabilizing the working LangGraph pipeline. Port **only the fairness/action drafting step**, since it's new code anyway (lower regression risk than porting a working node).

### 2.1 Install

```bash
pip install strands-agents
```

### 2.2 Scope decision (do not deviate from this)

- **Keep:** router, planner, research, RAG, vision, reflection nodes exactly as-is on LangGraph.
- **Port to Strands:** the action/drafting agent only (`Agents/action.py`, net-new in Task 3) — it has no existing working version to regress, and it's a bounded, single-purpose agent (input: violation list → output: drafted letter), which is exactly the shape Strands is designed for.
- **Do not** attempt to replace the router or reflection loop with Strands mid-hackathon — that is a rewrite of working infrastructure under time pressure, which is the single highest-risk move available to you this week.

### 2.3 Wrap the Strands agent so LangGraph can still call it as a normal node

**New file: `Agents/action.py`**

```python
from strands import Agent, tool
from Agents.state import AgentState

@tool
def draft_samadhaan_complaint(violation: dict, cited_law: str) -> str:
    """Strands tool: drafts a Samadhaan-portal-ready complaint paragraph."""
    ...

strands_action_agent = Agent(
    tools=[draft_samadhaan_complaint],
    model="bedrock/claude",   # confirm exact Bedrock model id string against Strands docs
)

async def action_node(state: AgentState) -> AgentState:
    """
    LangGraph-compatible wrapper around a Strands agent.
    Keeps the node signature identical to every other node in Agents/,
    so router.py and graph.py need zero changes to call it.
    """
    drafts = []
    for violation in state.fairness_violations:
        result = await strands_action_agent.invoke_async(
            f"Draft a Samadhaan complaint for: {violation}"
        )
        drafts.append(result)
    state.action_drafts = drafts
    return state
```

This pattern — Strands agent internally, plain async function externally — means the rest of your LangGraph graph never knows Strands exists. If Strands integration has issues under time pressure, you can swap `action_node`'s internals back to a direct Bedrock call without touching `router.py` or `graph.py` at all.

### 2.4 Fallback plan (write this now, not during a Day-3 panic)

If Strands integration breaks or eats too much time: keep `action_node`'s function signature, replace its body with a direct `bedrock_client.invoke_model(...)` call. Nothing else in the graph changes. Budget max 3–4 hours on Strands before falling back — this is a "nice to have AWS-native credit" item, not core functionality.

---

## Task 3 — Consolidated technical improvements (from prior review passes)

Execute in this order; each is independent and can be skipped without breaking the others if time runs out.

### 3.1 Bedrock as primary LLM path (not fallback)
- In `utils/config.py`: make Bedrock the default client; Groq becomes the explicit fallback (`if not BEDROCK_AVAILABLE: use_groq()`), never the reverse.
- Confirm this by grepping the codebase for the actual hot-path client call before the demo — the fix must be true in the code that runs, not just in the config comment.

### 3.2 Swap Postgres/Aurora → DynamoDB for SaaS tables
- Tables: `organizations`, `org_members`, `usage_events`, `api_keys`, `plan_limits`.
- Use single-table or per-entity design with PK `org_id`, SK pattern for `usage_events` (`SK = "USAGE#<ISO timestamp>"`) so month-range queries are a native sort-key condition, no expression indexes needed.
- Delete the Postgres-specific `date_trunc` index workaround entirely — it's not needed with this design.

### 3.3 Fix the quota key-mapping bug (if not already fixed)
```python
EVENT_TYPE_TO_LIMIT_KEY = {
    "analysis": "analyses", "document": "documents", "chat": "chat_messages",
}
```
Never derive the plan-limit key via string concatenation (`event_type + "s"`) — verify this explicitly in code review, not just by reading a comment claiming it's fixed.

### 3.4 Fix org-scoped endpoint IDOR
- `GET /api/org/{org_id}`, `/usage`, `/history`, `POST /invite` must call a real `verify_org_access(user, org_id, required_role=None)` function that:
  1. Looks up the caller's actual membership row for `org_id`.
  2. Raises 403 if no membership exists.
  3. For `/invite` specifically, also checks `role in ("admin", "owner")`.
- Write this function and show its body — do not mark this task complete based on a route comment alone.

### 3.5 Fix blocking synchronous calls inside async endpoints
- Audit every `async def` for a synchronous SDK call (Razorpay's `client.order.create`, any raw `sqlite3`/`psycopg2` call, `requests.get`, etc.).
- Wrap each with `await anyio.to_thread.run_sync(fn, *args)`.

### 3.6 Structured output schema everywhere
- `ViolationItem` / `AnalysisReport` Pydantic models (already specified) become the return type of every fairness/action node — no free-text LLM output reaches the API response layer unvalidated.

### 3.7 Textract structured extraction, not generic OCR
- Use `AnalyzeExpense` for bills/invoices, `AnalyzeDocument` with `FORMS`+`TABLES` for contracts/POs — replaces or supplements `pytesseract` for structured line-item fields the Cedar rules need (`paymentDays`, etc.).

### 3.8 Step Functions + EventBridge wiring
- S3 upload → EventBridge rule → Step Functions execution → invokes the Lambda/App Runner endpoint that runs the LangGraph pipeline.
- Deliverable: a Step Functions state-machine diagram screenshot for the demo video/README.

### 3.9 Bedrock Guardrails as a second safety layer
- Add alongside (not instead of) `guardrails/output_guard.py` — apply to the action agent's drafted output specifically, since fabricated legal citations are the highest-severity failure mode.

### 3.10 Real test coverage number
- Run `pytest tests/ --cov=. --cov-report=term-missing` and put the actual percentage in the README — replace any "target" language.

---

## Execution order recommendation (if time-constrained)

1. Task 1 (Cedar) — this is your core differentiator, do not skip or truncate
2. 3.1, 3.3, 3.4, 3.5 — correctness/security fixes, cheap and high-consequence if skipped
3. 3.7 (Textract structured extraction) — directly feeds Cedar's input fields, do before Task 1 testing
4. 3.2 (DynamoDB) — do only if Postgres is already causing friction; otherwise lower priority than it looks
5. Task 2 (Strands) — do last, time-boxed, with the fallback plan pre-written
6. 3.8, 3.9, 3.10 — do if Day 4 morning has slack; otherwise state as "roadmap" in the pitch, not as done