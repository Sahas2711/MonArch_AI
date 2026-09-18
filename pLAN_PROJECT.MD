Add 5 "Smoothness B" Features to Vasooli/Wemboo
Goal: Add Risk Score, Decision Recommendation, Evidence Panel improvements, Financial Impact Calculator, and Negotiation Recommendation — all built from existing data/logic, no new infrastructure or models.

Proposed Changes
Component 1 — Risk Score (Rule-Based)
Replaces the current opaque weighted scorer with a transparent, defensible deduction model that labels itself correctly.

[MODIFY] 
scorer.py
Current state: ComplianceScorer.calculate_score() uses WEIGHTS dict (payment_cycle=35, interest_penalty=30, tax_disallowance=20, unilateral_cancellation=15) and simple interest math. The weights silently sum to 100 and there's no per-deduction rationale or evidence confidence factor.

Changes:

Replace WEIGHTS with a new RISK_DEDUCTIONS dict matching the user's spec:
python

RISK_DEDUCTIONS = {
    "payment_days_breach":        (35, "Payment-term breach is weighted highest because it's the statute's core protection"),
    "no_penalty_interest_clause":  (20, "Missing penalty interest removes the statutory deterrent against delayed payments"),
    "unilateral_cancellation":     (15, "One-sided cancellation exposes the MSME to uncompensated losses"),
    "low_evidence_confidence":     (10, "Low extraction confidence means the determination may be unreliable"),
}
Add a new RiskScoreBreakdown Pydantic model with deduction_name, points_deducted, rationale, triggered fields.
Rework calculate_score() to:
Start at 100
Deduct 35 if payment_days > 45
Deduct 20 if no_penalty_interest_clause (any clause has has_penalty_interest == False)
Deduct 15 if unilateral_cancellation detected
Deduct 10 if average extraction confidence < 0.7
max(score, 0)
Return full breakdown list (which deductions fired and which didn't)
Map score to color band: ≥70 → green/low, 40–69 → amber/medium, <40 → red/high-critical
Keep existing ComplianceScore model but add breakdown_items: List[RiskScoreBreakdown] and score_disclaimer: str (hardcoded to "Calculated from flagged statutory violations — not a probability estimate.")
Rename score field description from "Overall compliance score" to "Compliance Risk Score (Rule-Based Risk Index)"
[MODIFY] 
schemas.py
Add to AnalysisReport:

python

risk_score_breakdown: Optional[List[dict]] = Field(None, description="Per-deduction breakdown of the Compliance Risk Score")
risk_score_disclaimer: str = Field(
    "Calculated from flagged statutory violations — not a probability estimate.",
    description="Mandatory labeling disclaimer for the risk score"
)
[MODIFY] 
api.py
 — analyse_contract endpoint (~line 695–710)
After scorer.calculate_score(), propagate the new breakdown_items and score_disclaimer into the AnalysisReport constructor.

Component 2 — Decision Recommendation (A/B/C Ladder)
A fixed if/elif decision tree, not a model. Needs only two new fields on the case record: contact_attempts and first_contact_date.

[NEW] 
recommender.py
New module with:

python

@dataclass
class RecommendedAction:
    action_id: str          # "send_demand" | "formal_notice" | "file_samadhaan"
    label: str              # "Send Payment Demand" | "Formal Legal Notice" | "File MSEFC/Samadhaan Complaint"
    effort_level: str       # "low" | "medium" | "high"
    is_recommended: bool
    reason: str             # "Recommended because no prior contact has been made."
    escalation_order: int   # 1, 2, 3
class DecisionRecommender:
    def recommend(self, has_violations: bool, contact_attempts: int,
                  first_contact_date: Optional[date], current_date: Optional[date] = None
    ) -> List[RecommendedAction]:
Logic (exactly as user specified):

contact_attempts == 0 → recommend "Send Payment Demand"
contact_attempts > 0 and days_since_first_contact < 30 → recommend "Formal Legal Notice"
contact_attempts > 0 and days_since_first_contact >= 30 → recommend "File MSEFC/Samadhaan Complaint"
Always returns all 3 options with is_recommended=True on exactly one.

[MODIFY] 
schemas.py
Add new schemas:

python

class RecommendedActionSchema(BaseModel):
    action_id: str
    label: str
    effort_level: str
    is_recommended: bool
    reason: str
    escalation_order: int
class CaseTrackingFields(BaseModel):
    contact_attempts: int = 0
    first_contact_date: Optional[str] = None
Add to AnalysisReport:

python

recommended_actions: Optional[List[RecommendedActionSchema]] = None
contact_attempts: int = Field(0, description="Number of contact attempts made for this case")
first_contact_date: Optional[str] = Field(None, description="ISO date of first contact attempt")
[MODIFY] 
db.py
 — init_sqlite_db()
Add two columns to analyses_history:

sql

ALTER TABLE analyses_history ADD COLUMN contact_attempts INTEGER DEFAULT 0;
ALTER TABLE analyses_history ADD COLUMN first_contact_date TEXT;
(Wrapped in try/except for idempotency since SQLite ALTER TABLE doesn't support IF NOT EXISTS.)

[MODIFY] 
schema.sql
 — analyses_history table
Add:

sql

contact_attempts   INTEGER NOT NULL DEFAULT 0,
first_contact_date TIMESTAMPTZ
[MODIFY] 
api.py
In analyse_contract (~line 695): call DecisionRecommender.recommend(...) with initial contact_attempts=0 and attach to report.
New endpoint POST /api/analyses/{report_id}/contact — increments contact_attempts, sets first_contact_date on first call, re-runs DecisionRecommender, and returns updated recommendation. This is the "mark as sent" button handler.
Component 3 — Evidence Panel (Backend Improvements)
ViolationItem already has the right fields. The gap is: start_char/end_char are never populated, and there's no page_number or clause_reference.

[MODIFY] 
extractor.py
In all three extraction helpers (_extract_payment_terms, _extract_interest_terms, _extract_cancellation_terms):

Actually populate start_char and end_char from match.start() / match.end() (the regex match objects are already available but their offsets are discarded).
Add a simple page estimation heuristic: page_number = (start_char // avg_chars_per_page) + 1 where avg_chars_per_page ≈ 3000 (reasonable for A4 text). This is a rough estimate for plain-text; for actual PDFs ingested via Textract, Textract already returns page numbers which should be threaded through.
Extract clause reference (e.g., "§14.2", "Clause 7.1") via a new regex pattern:
python

CLAUSE_REF_PATTERN = r'(?:clause|section|article|§)\s*(\d+(?:\.\d+)*)'
Search near the matched region and attach as clause_reference on ExtractedClause.
[MODIFY] 
schemas.py
 — EvidenceItem
Add:

python

page_number: Optional[int] = Field(None, description="Estimated or Textract-derived page number in source document")
clause_reference: Optional[str] = Field(None, description="Contract clause reference (e.g. §14.2, Clause 7.1)")
[MODIFY] 
schemas.py
 — ExtractedClause (in pipeline/extractor.py)
Add:

python

page_number: Optional[int] = Field(None, description="Estimated page number")
clause_reference: Optional[str] = Field(None, description="Clause/section reference identifier")
[MODIFY] 
api.py
 — analyse_contract
When constructing ViolationItem objects (~lines 530–680), propagate start_char, end_char, page_number, and clause_reference from the matched ExtractedClause into the EvidenceItem.

Component 4 — Financial Impact Calculator (Compound Interest)
This is the one correctness-critical item. Section 16 mandates compound interest with monthly rests at 3× RBI bank rate.

[NEW] 
financial.py
New standalone module:

python

def month_diff(start: date, end: date) -> int:
    """Exact number of complete calendar months between two dates."""
    return (end.year - start.year) * 12 + (end.month - start.month)
def calculate_statutory_interest(
    principal: float,
    due_date: date,
    payment_date: date,
    rbi_rate: float = 6.5
) -> StatutoryInterestResult:
    """
    Section 16 MSMED Act 2006: compound interest with monthly rests
    at 3× RBI bank rate from due_date to payment_date.
    """
    monthly_rate = (3 * rbi_rate) / 12 / 100
    months_overdue = month_diff(due_date, payment_date)
    interest = principal * ((1 + monthly_rate) ** months_overdue - 1)
    return StatutoryInterestResult(
        principal=principal,
        due_date=due_date,
        payment_date=payment_date,
        delay_days=(payment_date - due_date).days,
        months_overdue=months_overdue,
        rbi_bank_rate=rbi_rate,
        statutory_rate=3 * rbi_rate,
        monthly_rate=round(monthly_rate * 100, 4),
        interest_amount=round(interest, 2),
        total_recoverable=round(principal + interest, 2),
    )
StatutoryInterestResult is a Pydantic model with all breakdown fields for the UI display.

IMPORTANT

Verification requirement: Before trusting this function, I will write a unit test with a hand-calculated example. For instance: ₹10,00,000 principal, 90 days overdue (3 months), RBI rate 6.5% → monthly rate = (3 × 6.5) / 12 / 100 = 0.01625 → interest = 10,00,000 × ((1.01625)³ − 1) = ₹49,565.86. The test will assert this exact value.

[MODIFY] 
scorer.py
Replace the simple interest line (contract_value * daily_interest_rate * effective_delay_days) with a call to calculate_statutory_interest() from the new financial.py, using sensible defaults for due_date (today - delay_days) and payment_date (today).

[MODIFY] 
api.py
 — analyse_contract
Replace the inline interest calculations (~lines 540, 580) with calls to calculate_statutory_interest().
Add financial_breakdown field to the response containing the full StatutoryInterestResult for the UI's "wow" screen.
[MODIFY] 
schemas.py
 — FinancialImpact
Add detailed breakdown fields:

python

months_overdue: Optional[int] = Field(None, description="Complete calendar months of overdue payment")
monthly_compound_rate: Optional[float] = Field(None, description="Monthly compound interest rate applied (%)")
rbi_bank_rate: Optional[float] = Field(None, description="RBI bank rate used for calculation")
principal_amount: Optional[float] = Field(None, description="Invoice/contract principal amount")
total_recoverable: Optional[float] = Field(None, description="Principal + compound interest = total claim")
calculation_method: str = Field("compound_monthly_rests", description="Interest compounding method used")
[NEW] 
test_financial.py
Unit tests:

Hand-calculated compound interest: ₹10,00,000, 3 months overdue, RBI 6.5% → ₹49,565.86 interest
Zero delay: 0 months → ₹0 interest
Edge case: same due_date and payment_date → ₹0
Large delay: 12 months overdue → verify against manual calculation
month_diff correctness: various date pairs
Component 5 — Negotiation Recommendation (Pre-Signature Clause Rewrite)
Reuse the existing action agent's clause-drafting logic with a different entry point and framing.

[MODIFY] 
action.py
Add a new function negotiate_clause(clause_text: str, violation_type: str, cited_law: str) -> str that:

Uses the same Strands agent / LLM fallback pattern as action_node
But with a different prompt template framed for pre-signature review:

"You are reviewing a contract clause BEFORE signing. Rewrite this clause to be MSME-compliant.
 Original clause: {clause_text}
 Violation: {violation_type} under {cited_law}
 Provide: 1) The compliant replacement clause, 2) One sentence explaining why the original is risky."
Returns a NegotiationResult with original_clause, compliant_replacement, risk_explanation
[MODIFY] 
schemas.py
Add:

python

class NegotiationRecommendation(BaseModel):
    original_clause: str
    violation_type: str
    cited_law: str
    compliant_replacement: str
    risk_explanation: str
    confidence: float
Add to AnalysisReport:

python

negotiation_recommendations: Optional[List[NegotiationRecommendation]] = None
[MODIFY] 
api.py
 — analyse_contract
After building violations, call negotiate_clause() for each violation that has a draft_counter_clause and attach results as negotiation_recommendations on the report. This reuses the existing draft_counter_clause data as a deterministic fallback, with the LLM providing enhanced framing.

[NEW endpoint] 
api.py
 — POST /api/negotiate
New endpoint that accepts a single clause text + context and returns a NegotiationRecommendation. This is the "review before signing" entry point, separate from the full analysis pipeline:

python

class NegotiateRequest(BaseModel):
    clause_text: str
    buyer_name: Optional[str] = None
    contract_value: Optional[float] = None
@app.post("/api/negotiate", tags=["Core Product"])
async def negotiate_clause_endpoint(req: NegotiateRequest, user: UserContext = Depends(get_current_user)):
    # 1. Extract clause → 2. Cedar evaluate → 3. For each violation, negotiate_clause()
    # Returns List[NegotiationRecommendation]
Summary of All File Changes
File	Action	Component
pipeline/scorer.py
MODIFY	1 (Risk Score) + 4 (use compound interest)
pipeline/recommender.py
NEW	2 (Decision Recommendation)
pipeline/financial.py
NEW	4 (Financial Calculator)
pipeline/extractor.py
MODIFY	3 (Evidence Panel — populate offsets/page/clause ref)
pipeline/__init__.py
MODIFY	Export new classes
models/schemas.py
MODIFY	1, 2, 3, 4, 5 (new fields + schemas)
Agents/action.py
MODIFY	5 (Negotiation — new negotiate_clause())
api.py
MODIFY	1, 2, 3, 4, 5 (update analyse, new endpoints)
SQL/db.py
MODIFY	2 (add contact_attempts columns)
SQL/schema.sql
MODIFY	2 (add contact_attempts columns)
tests/test_financial.py
NEW	4 (compound interest unit tests)
tests/test_scorer.py
NEW	1 (risk score unit tests)
tests/test_recommender.py
NEW	2 (decision ladder unit tests)
Open Questions
IMPORTANT

RBI Bank Rate source: The current code hardcodes 6.5%. Should this remain hardcoded for now, or should we add an env var / config field so it can be updated when RBI changes the rate? (The rate changes ~2-4× per year.)

IMPORTANT

Contact tracking scope: The "mark as sent" endpoint (POST /api/analyses/{report_id}/contact) — should it also log an audit event via audit/logger.py, or is simple DB update sufficient for now?

IMPORTANT

Negotiation endpoint auth: Should POST /api/negotiate count against the org's monthly analysis quota, or should it be treated as a separate (cheaper) quota bucket? It runs less compute than a full analysis.

Verification Plan
Automated Tests
bash

# Unit tests for financial calculator (hand-calculated compound interest)
pytest tests/test_financial.py -v
# Unit tests for risk score deductions
pytest tests/test_scorer.py -v
# Unit tests for decision recommendation ladder
pytest tests/test_recommender.py -v
# Full test suite
pytest tests/ -v --tb=short
Manual Verification
Risk Score: Run POST /api/analyse with a 90-day payment clause + no interest + unilateral cancellation → expect score = 100 - 35 - 20 - 15 = 30 (critical/red), with all 3 deductions visible in breakdown
Decision Ladder: Call POST /api/analyses/{id}/contact twice, verify recommendation escalates from "Send Demand" → "Formal Notice" → (after 30 days) "File Samadhaan"
Evidence Panel: Verify page_number, clause_reference, start_char, end_char are populated in violation evidence items
Financial Calculator: Compare ₹15,00,000 × 3 months overdue output against manual Excel calculation
Negotiation: Call POST /api/negotiate with a violating clause, verify compliant replacement is returned
Build Verification
bash

# Ensure API starts cleanly
python main.py --serve-api
# Hit health endpoint
curl http://localhost:8000/api/health