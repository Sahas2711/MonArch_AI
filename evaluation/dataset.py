"""
Curated MSME Payment Compliance Evaluation Dataset.

Contains 30+ labeled ground-truth test cases across:
- Section 15 45-day payment cap violations (numeric and word-based)
- Section 16 statutory interest violations (explicit waivers, silent contracts)
- Unilateral termination and unfair commercial terms
- Section 43B(h) tax disallowance scenarios
- Fully compliant contracts (True Negatives)
- Ambiguous and edge case clauses
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A labeled ground-truth test case for MSME compliance evaluation."""
    id: str
    category: str = Field(..., description="payment_cycle | interest_penalty | cancellation | compliant | edge_case")
    contract_text: str
    expected_payment_days: Optional[int] = None
    expected_has_penalty_interest: Optional[bool] = None
    expected_has_unilateral_cancellation: Optional[bool] = None
    expected_violations: List[str] = Field(default_factory=list)
    expected_risk_level: str = "medium"
    expected_min_score: int = 0
    expected_max_score: int = 100
    expected_needs_review: bool = False
    description: str = ""


# Comprehensive 30+ labeled MSME compliance evaluation dataset
EVAL_DATASET: List[EvalCase] = [
    # -------------------------------------------------------------------------
    # 1-6: Standard Payment Term Violations (Section 15 MSMED Act)
    # -------------------------------------------------------------------------
    EvalCase(
        id="case_01",
        category="payment_cycle",
        contract_text="Payment shall be released by the Buyer within 90 days from receipt of accepted goods.",
        expected_payment_days=90,
        expected_violations=["payment_cycle", "tax_disallowance"],
        expected_risk_level="high",
        expected_min_score=30,
        expected_max_score=65,
        expected_needs_review=False,
        description="Standard 90-day payment term exceeding 45-day cap",
    ),
    EvalCase(
        id="case_02",
        category="payment_cycle",
        contract_text="Invoice settlement will be processed on net 60 days basis from invoice submission.",
        expected_payment_days=60,
        expected_violations=["payment_cycle", "tax_disallowance"],
        expected_risk_level="high",
        expected_min_score=40,
        expected_max_score=70,
        expected_needs_review=False,
        description="Net 60 payment terms exceeding Section 15 limit",
    ),
    EvalCase(
        id="case_03",
        category="payment_cycle",
        contract_text="Disbursement timeline: All payments shall be made within ninety days following QA clearance.",
        expected_payment_days=90,
        expected_violations=["payment_cycle", "tax_disallowance"],
        expected_risk_level="high",
        expected_min_score=30,
        expected_max_score=65,
        expected_needs_review=False,
        description="Payment days written in words (ninety days)",
    ),
    EvalCase(
        id="case_04",
        category="payment_cycle",
        contract_text="Credit period granted to the purchaser shall be 120 days from the date of consignment arrival.",
        expected_payment_days=120,
        expected_violations=["payment_cycle", "tax_disallowance"],
        expected_risk_level="high",
        expected_min_score=20,
        expected_max_score=65,
        expected_needs_review=False,
        description="Severe credit period of 120 days",
    ),
    EvalCase(
        id="case_05",
        category="payment_cycle",
        contract_text="Payment terms: seventy-five days from delivery of materials at project site.",
        expected_payment_days=75,
        expected_violations=["payment_cycle", "tax_disallowance"],
        expected_risk_level="high",
        expected_min_score=35,
        expected_max_score=70,
        expected_needs_review=False,
        description="Hyphenated word payment term (seventy-five days)",
    ),
    EvalCase(
        id="case_06",
        category="payment_cycle",
        contract_text="The supplier agrees to credit terms of one hundred twenty days from bill date.",
        expected_payment_days=120,
        expected_violations=["payment_cycle", "tax_disallowance"],
        expected_risk_level="high",
        expected_min_score=20,
        expected_max_score=65,
        expected_needs_review=False,
        description="Long word payment term (one hundred twenty days)",
    ),

    # -------------------------------------------------------------------------
    # 7-12: Interest Penalty Violations (Section 16 MSMED Act)
    # -------------------------------------------------------------------------
    EvalCase(
        id="case_07",
        category="interest_penalty",
        contract_text="Payment within 30 days. Under no circumstances shall interest accrue on delayed disbursements.",
        expected_payment_days=30,
        expected_has_penalty_interest=False,
        expected_violations=["interest_penalty"],
        expected_risk_level="medium",
        expected_min_score=60,
        expected_max_score=80,
        expected_needs_review=False,
        description="Explicit interest waiver on delayed payment",
    ),
    EvalCase(
        id="case_08",
        category="interest_penalty",
        contract_text="All invoices payable in 30 days. Vendor agrees that no penalty or interest shall be claimed for late payments.",
        expected_payment_days=30,
        expected_has_penalty_interest=False,
        expected_violations=["interest_penalty"],
        expected_risk_level="medium",
        expected_min_score=60,
        expected_max_score=80,
        expected_needs_review=False,
        description="Vendor forced waiver of penalty and interest",
    ),
    EvalCase(
        id="case_09",
        category="interest_penalty",
        contract_text="Payment within 45 days. The transaction is interest-free and no late payment compensation will be entertained.",
        expected_payment_days=45,
        expected_has_penalty_interest=False,
        expected_violations=["interest_penalty"],
        expected_risk_level="medium",
        expected_min_score=60,
        expected_max_score=80,
        expected_needs_review=False,
        description="Interest-free clause conflicting with Sec 16",
    ),
    EvalCase(
        id="case_10",
        category="interest_penalty",
        contract_text="Payment period is 30 days. Supplier waives all right to interest on any outstanding balances.",
        expected_payment_days=30,
        expected_has_penalty_interest=False,
        expected_violations=["interest_penalty"],
        expected_risk_level="medium",
        expected_min_score=60,
        expected_max_score=80,
        expected_needs_review=False,
        description="Explicit waiver of right to interest",
    ),
    EvalCase(
        id="case_11",
        category="interest_penalty",
        contract_text="Disbursements made within 30 days without interest under any circumstances.",
        expected_payment_days=30,
        expected_has_penalty_interest=False,
        expected_violations=["interest_penalty"],
        expected_risk_level="medium",
        expected_min_score=60,
        expected_max_score=80,
        expected_needs_review=False,
        description="Without interest condition",
    ),
    EvalCase(
        id="case_12",
        category="interest_penalty",
        contract_text="Settlement within 15 days. No claim for interest shall be admissible against the purchaser.",
        expected_payment_days=15,
        expected_has_penalty_interest=False,
        expected_violations=["interest_penalty"],
        expected_risk_level="medium",
        expected_min_score=60,
        expected_max_score=80,
        expected_needs_review=False,
        description="No claim for interest admissible",
    ),

    # -------------------------------------------------------------------------
    # 13-17: Unilateral Cancellation / Unfair Terms
    # -------------------------------------------------------------------------
    EvalCase(
        id="case_13",
        category="cancellation",
        contract_text="Buyer reserves the unilateral right to cancel the order without notice at any time without liability.",
        expected_has_unilateral_cancellation=True,
        expected_violations=["unilateral_cancellation"],
        expected_risk_level="medium",
        expected_min_score=70,
        expected_max_score=90,
        expected_needs_review=False,
        description="Unilateral cancellation without notice or liability",
    ),
    EvalCase(
        id="case_14",
        category="cancellation",
        contract_text="Payment within 30 days. The purchaser may terminate at buyer's sole discretion without compensation.",
        expected_payment_days=30,
        expected_has_unilateral_cancellation=True,
        expected_violations=["unilateral_cancellation"],
        expected_risk_level="medium",
        expected_min_score=70,
        expected_max_score=90,
        expected_needs_review=False,
        description="Termination at purchaser sole discretion without compensation",
    ),
    EvalCase(
        id="case_15",
        category="cancellation",
        contract_text="The client holds the right to cancel at any time without assigning any reason.",
        expected_has_unilateral_cancellation=True,
        expected_violations=["unilateral_cancellation"],
        expected_risk_level="medium",
        expected_min_score=70,
        expected_max_score=90,
        expected_needs_review=False,
        description="Cancel at any time without assigning reason",
    ),
    EvalCase(
        id="case_16",
        category="cancellation",
        contract_text="Company may unilaterally modify or terminate the purchase agreement without notice.",
        expected_has_unilateral_cancellation=True,
        expected_violations=["unilateral_cancellation"],
        expected_risk_level="medium",
        expected_min_score=70,
        expected_max_score=90,
        expected_needs_review=False,
        description="Unilateral modification or termination",
    ),
    EvalCase(
        id="case_17",
        category="cancellation",
        contract_text="Buyer may cancel the contract without notice if delivery deviates by even one hour.",
        expected_has_unilateral_cancellation=True,
        expected_violations=["unilateral_cancellation"],
        expected_risk_level="medium",
        expected_min_score=70,
        expected_max_score=90,
        expected_needs_review=False,
        description="Cancellation without notice on minor deviation",
    ),

    # -------------------------------------------------------------------------
    # 18-23: Combined Multi-Violation Clauses (High Risk)
    # -------------------------------------------------------------------------
    EvalCase(
        id="case_18",
        category="combined",
        contract_text="Payment shall be made within 90 days. No interest shall accrue on delayed disbursements. Buyer may cancel at any time without notice.",
        expected_payment_days=90,
        expected_has_penalty_interest=False,
        expected_has_unilateral_cancellation=True,
        expected_violations=["payment_cycle", "interest_penalty", "unilateral_cancellation", "tax_disallowance"],
        expected_risk_level="critical",
        expected_min_score=0,
        expected_max_score=25,
        expected_needs_review=False,
        description="Triple violation: 90 days + no interest + unilateral cancellation",
    ),
    EvalCase(
        id="case_19",
        category="combined",
        contract_text="Settlement on net 60 days. Interest free transaction with right to cancel without notice.",
        expected_payment_days=60,
        expected_has_penalty_interest=False,
        expected_has_unilateral_cancellation=True,
        expected_violations=["payment_cycle", "interest_penalty", "unilateral_cancellation", "tax_disallowance"],
        expected_risk_level="critical",
        expected_min_score=0,
        expected_max_score=35,
        expected_needs_review=False,
        description="Net 60 + interest free + cancellation without notice",
    ),
    EvalCase(
        id="case_20",
        category="combined",
        contract_text="Credit period of ninety days. Supplier waives interest and buyer may terminate at sole discretion.",
        expected_payment_days=90,
        expected_has_penalty_interest=False,
        expected_has_unilateral_cancellation=True,
        expected_violations=["payment_cycle", "interest_penalty", "unilateral_cancellation", "tax_disallowance"],
        expected_risk_level="critical",
        expected_min_score=0,
        expected_max_score=30,
        expected_needs_review=False,
        description="Ninety days + interest waiver + sole discretion termination",
    ),
    EvalCase(
        id="case_21",
        category="combined",
        contract_text="Payment within 120 days from delivery. Without interest under any circumstances.",
        expected_payment_days=120,
        expected_has_penalty_interest=False,
        expected_violations=["payment_cycle", "interest_penalty", "tax_disallowance"],
        expected_risk_level="critical",
        expected_min_score=10,
        expected_max_score=40,
        expected_needs_review=False,
        description="120 days + without interest",
    ),
    EvalCase(
        id="case_22",
        category="combined",
        contract_text="Payment terms 75 days. No penalty or interest on late disbursements.",
        expected_payment_days=75,
        expected_has_penalty_interest=False,
        expected_violations=["payment_cycle", "interest_penalty", "tax_disallowance"],
        expected_risk_level="critical",
        expected_min_score=15,
        expected_max_score=45,
        expected_needs_review=False,
        description="75 days + no late interest",
    ),
    EvalCase(
        id="case_23",
        category="combined",
        contract_text="Net 90 days payment. Buyer reserves right to cancel without notice.",
        expected_payment_days=90,
        expected_has_unilateral_cancellation=True,
        expected_violations=["payment_cycle", "unilateral_cancellation", "tax_disallowance"],
        expected_risk_level="critical",
        expected_min_score=20,
        expected_max_score=55,
        expected_needs_review=False,
        description="Net 90 + cancel without notice",
    ),

    # -------------------------------------------------------------------------
    # 24-28: Fully Compliant Contracts (True Negatives)
    # -------------------------------------------------------------------------
    EvalCase(
        id="case_24",
        category="compliant",
        contract_text="Payment shall be made in full within 30 days of invoice receipt. Delayed payments shall attract compound interest at 3x RBI bank rate.",
        expected_payment_days=30,
        expected_has_penalty_interest=True,
        expected_has_unilateral_cancellation=False,
        expected_violations=[],
        expected_risk_level="low",
        expected_min_score=85,
        expected_max_score=100,
        expected_needs_review=False,
        description="Fully compliant 30-day payment with explicit 3x RBI statutory interest",
    ),
    EvalCase(
        id="case_25",
        category="compliant",
        contract_text="Payment within 45 days from acceptance. In event of delay, interest with monthly rests under Section 16 of MSME Act shall apply.",
        expected_payment_days=45,
        expected_has_penalty_interest=True,
        expected_has_unilateral_cancellation=False,
        expected_violations=[],
        expected_risk_level="low",
        expected_min_score=85,
        expected_max_score=100,
        expected_needs_review=False,
        description="Compliant 45-day term citing Section 16 MSME Act",
    ),
    EvalCase(
        id="case_26",
        category="compliant",
        contract_text="All payments shall be released within fifteen days of bill certification.",
        expected_payment_days=15,
        expected_violations=[],
        expected_risk_level="low",
        expected_min_score=85,
        expected_max_score=100,
        expected_needs_review=False,
        description="Short compliant 15-day cycle",
    ),
    EvalCase(
        id="case_27",
        category="compliant",
        contract_text="Advance payment of 50% upon purchase order and remaining 50% within 30 days of delivery.",
        expected_payment_days=30,
        expected_violations=[],
        expected_risk_level="low",
        expected_min_score=85,
        expected_max_score=100,
        expected_needs_review=False,
        description="Milestone advance + 30-day balance payment",
    ),
    EvalCase(
        id="case_28",
        category="compliant",
        contract_text="Payment terms: within forty-five days from receipt of goods. Either party may terminate with 30 days mutual written notice.",
        expected_payment_days=45,
        expected_has_unilateral_cancellation=False,
        expected_violations=[],
        expected_risk_level="low",
        expected_min_score=85,
        expected_max_score=100,
        expected_needs_review=False,
        description="Compliant 45-day term with bilateral 30-day notice termination",
    ),

    # -------------------------------------------------------------------------
    # 29-33: Ambiguous and Edge Case Clauses (Human-in-the-Loop Triggers)
    # -------------------------------------------------------------------------
    EvalCase(
        id="case_29",
        category="edge_case",
        contract_text="Payment will be processed subject to client funds availability at the end of the quarter.",
        expected_violations=[],
        expected_needs_review=True,
        description="Vague conditional payment without explicit timeline",
    ),
    EvalCase(
        id="case_30",
        category="edge_case",
        contract_text="Standard commercial terms apply as agreed separately in annexure B.",
        expected_violations=[],
        expected_needs_review=True,
        description="Reference to external annexure with no embedded terms",
    ),
    EvalCase(
        id="case_31",
        category="edge_case",
        contract_text="Disbursement following milestone signoff as per project governance schedule.",
        expected_violations=[],
        expected_needs_review=True,
        description="Milestone phrasing without explicit day count",
    ),
    EvalCase(
        id="case_32",
        category="edge_case",
        contract_text="All invoices cleared subject to audit committee review within reasonable business time.",
        expected_violations=[],
        expected_needs_review=True,
        description="Subjective 'reasonable business time' phrase",
    ),
    EvalCase(
        id="case_33",
        category="edge_case",
        contract_text="General service agreement. Terms shall be mutually discussed upon receipt of deliverables.",
        expected_violations=[],
        expected_needs_review=True,
        description="Deferred payment terms negotiation",
    ),
]
