"""
Policy Evaluator Module.

Evaluates extracted contractual facts against versioned policy rules to produce
deterministic, auditable PolicyDecision records.

KEY ARCHITECTURAL RULE:
    The determination of violation belongs exclusively to the Policy Evaluator.
    Every decision must cite statute, section, exact fact IDs, and evidence IDs.
"""

from datetime import date
from typing import List, Optional
import uuid

from vasooli.domain.enums import DecisionOutcome, FactStatus, FactType, PaymentBasis, Severity
from vasooli.domain.models import ExtractedFact, PolicyDecision
from vasooli.finance.rate_config import get_current_rate_config
from vasooli.policy.msmed_act_rules import create_default_policy_registry
from vasooli.policy.rule_registry import PolicyRegistry


class PolicyEvaluator:
    """
    Evaluates ExtractedFact items against legal rules.
    """

    def __init__(self, registry: Optional[PolicyRegistry] = None):
        self.registry = registry or create_default_policy_registry()

    def evaluate(
        self,
        facts: List[ExtractedFact],
        evaluation_date: Optional[date] = None,
    ) -> List[PolicyDecision]:
        """
        Evaluates all facts and returns a list of PolicyDecisions.
        """
        eval_date = evaluation_date or date.today()
        decisions: List[PolicyDecision] = []

        for fact in facts:
            if fact.fact_type == FactType.PAYMENT_TERM:
                decisions.extend(self._evaluate_payment_fact(fact, eval_date))
            elif fact.fact_type == FactType.INTEREST_CLAUSE:
                decisions.extend(self._evaluate_interest_fact(fact, eval_date))
            elif fact.fact_type == FactType.CANCELLATION_CLAUSE:
                decisions.extend(self._evaluate_cancellation_fact(fact, eval_date))
            elif fact.fact_type == FactType.DISPUTE_RESOLUTION:
                decisions.extend(self._evaluate_dispute_fact(fact, eval_date))

        return decisions

    def _evaluate_payment_fact(
        self, fact: ExtractedFact, eval_date: date
    ) -> List[PolicyDecision]:
        """Evaluates MSMED Act Sec 15 and IT Act Sec 43B(h) on payment terms."""
        decisions = []
        val = fact.value
        days = val.get("days")
        basis = val.get("basis")
        has_written = val.get("has_written_agreement", True)
        status = fact.status

        rule_sec15 = self.registry.get_rule("MSMED_SEC15_PAYMENT_LIMIT", eval_date)
        rule_43bh = self.registry.get_rule("IT_ACT_SEC43BH_DISALLOWANCE", eval_date)

        # 1. Ambiguous or discretionary payment triggers (e.g. buyer approval without fixed deadline)
        if status == FactStatus.AMBIGUOUS or basis == PaymentBasis.BUYER_APPROVAL or basis == "buyer_approval":
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-PAY-AMB-{uuid.uuid4().hex[:6]}",
                    policy_id="MSMED_SEC15_PAYMENT_LIMIT",
                    decision=DecisionOutcome.INCONCLUSIVE,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation=(
                        f"Payment clause contains an ambiguous or delayed trigger: {fact.inconclusive_reason or 'Payment conditioned on buyer discretion/approval without a defined statutory deadline'}. "
                        "MSMED Act Section 15 requires payment within 45 days of acceptance or deemed acceptance. "
                        "Clauses delaying the trigger prevent deterministic compliance confirmation without reviewer clarification."
                    ),
                    policy_version=rule_sec15.version if rule_sec15 else "2026.1",
                    statute_ref="MSMED Act 2006, Section 15",
                    severity=Severity.HIGH,
                    review_status="pending",
                )
            )
            return decisions

        # 2. Inconclusive fact status
        if status == FactStatus.INCONCLUSIVE or days is None:
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-PAY-INC-{uuid.uuid4().hex[:6]}",
                    policy_id="MSMED_SEC15_PAYMENT_LIMIT",
                    decision=DecisionOutcome.INCONCLUSIVE,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation="Payment is mentioned but specific timeline or days count could not be deterministically extracted.",
                    policy_version=rule_sec15.version if rule_sec15 else "2026.1",
                    statute_ref="MSMED Act 2006, Section 15",
                    severity=Severity.MEDIUM,
                    review_status="pending",
                )
            )
            return decisions

        # 3. Deterministic days evaluation
        max_permitted_days = 45 if has_written else 15
        statute_condition_text = (
            "under written agreement (statutory max 45 days)"
            if has_written
            else "in absence of written agreement (statutory max 15 days)"
        )

        if days > max_permitted_days:
            # Direct Section 15 violation
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-PAY-VIO-{uuid.uuid4().hex[:6]}",
                    policy_id="MSMED_SEC15_PAYMENT_LIMIT",
                    decision=DecisionOutcome.TRIGGERED,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation=(
                        f"Payment period of {days} days exceeds statutory maximum of {max_permitted_days} days "
                        f"{statute_condition_text} from date of acceptance or deemed acceptance pursuant to Section 15 of MSMED Act 2006. "
                        "Any contractual term specifying a longer period is void under Section 24."
                    ),
                    policy_version=rule_sec15.version if rule_sec15 else "2026.1",
                    statute_ref="MSMED Act 2006, Section 15",
                    severity=Severity.HIGH,
                    review_status="pending",
                )
            )

            # Section 43B(h) Tax Disallowance Exposure
            if rule_43bh:
                decisions.append(
                    PolicyDecision(
                        decision_id=f"DEC-TAX-VIO-{uuid.uuid4().hex[:6]}",
                        policy_id="IT_ACT_SEC43BH_DISALLOWANCE",
                        decision=DecisionOutcome.TRIGGERED,
                        confidence=fact.confidence,
                        facts_used=[fact.fact_id],
                        evidence_ids=[fact.evidence.evidence_id],
                        explanation=(
                            f"Payment terms of {days} days breach Section 15 limit ({max_permitted_days} days). "
                            "Estimated potential tax disallowance exposure under Section 43B(h) of Income Tax Act 1961 "
                            "if invoices are not settled within the same financial year. Tax treatment requires professional confirmation."
                        ),
                        policy_version=rule_43bh.version,
                        statute_ref="Income Tax Act 1961, Section 43B(h)",
                        severity=Severity.HIGH,
                        review_status="pending",
                    )
                )
        else:
            # Compliant
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-PAY-OK-{uuid.uuid4().hex[:6]}",
                    policy_id="MSMED_SEC15_PAYMENT_LIMIT",
                    decision=DecisionOutcome.NOT_TRIGGERED,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation=(
                        f"Payment period of {days} days is within the statutory limit of {max_permitted_days} days "
                        f"{statute_condition_text} under Section 15 of MSMED Act 2006."
                    ),
                    policy_version=rule_sec15.version if rule_sec15 else "2026.1",
                    statute_ref="MSMED Act 2006, Section 15",
                    severity=Severity.LOW,
                    review_status="approved",
                )
            )

        return decisions

    def _evaluate_interest_fact(
        self, fact: ExtractedFact, eval_date: date
    ) -> List[PolicyDecision]:
        """Evaluates MSMED Act Sec 16 and Sec 24 on interest terms."""
        decisions = []
        val = fact.value
        waived = val.get("interest_waived")
        provided = val.get("interest_provided")
        rate_pct = val.get("interest_rate_percent")
        rule_sec16 = self.registry.get_rule("MSMED_SEC16_PENALTY_INTEREST", eval_date)

        # Look up current statutory annual rate for comparison
        rate_cfg = get_current_rate_config(eval_date)
        statutory_min_rate = float(rate_cfg.annual_statutory_rate_percent)  # e.g. 19.5%

        if waived is True or provided is False:
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-INT-VIO-{uuid.uuid4().hex[:6]}",
                    policy_id="MSMED_SEC16_PENALTY_INTEREST",
                    decision=DecisionOutcome.TRIGGERED,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation=(
                        "Contract clause waives or disallows interest on delayed payments. "
                        "Under Section 16 read with Section 24 of MSMED Act 2006, statutory compound interest "
                        f"at 3x RBI bank rate ({statutory_min_rate}% p.a.) with monthly rests is mandatory and cannot be contracted out of. "
                        "The waiver clause is void ab initio."
                    ),
                    policy_version=rule_sec16.version if rule_sec16 else "2026.1",
                    statute_ref="MSMED Act 2006, Section 16 & Section 24",
                    severity=Severity.HIGH,
                    review_status="pending",
                )
            )
        elif provided is True:
            # Check if rate is specified and below statutory minimum
            if rate_pct is not None and rate_pct < statutory_min_rate:
                decisions.append(
                    PolicyDecision(
                        decision_id=f"DEC-INT-SUB-{uuid.uuid4().hex[:6]}",
                        policy_id="MSMED_SEC16_PENALTY_INTEREST",
                        decision=DecisionOutcome.TRIGGERED,
                        confidence=fact.confidence,
                        facts_used=[fact.fact_id],
                        evidence_ids=[fact.evidence.evidence_id],
                        explanation=(
                            f"Contract provides interest at {rate_pct}% p.a., which is below statutory minimum of "
                            f"{statutory_min_rate}% p.a. (3x RBI bank rate) mandated by Section 16 of MSMED Act 2006. "
                            "The statutory rate overrides the contractual rate pursuant to Section 24."
                        ),
                        policy_version=rule_sec16.version if rule_sec16 else "2026.1",
                        statute_ref="MSMED Act 2006, Section 16 & Section 24",
                        severity=Severity.MEDIUM,
                        review_status="pending",
                    )
                )
            else:
                decisions.append(
                    PolicyDecision(
                        decision_id=f"DEC-INT-OK-{uuid.uuid4().hex[:6]}",
                        policy_id="MSMED_SEC16_PENALTY_INTEREST",
                        decision=DecisionOutcome.NOT_TRIGGERED,
                        confidence=fact.confidence,
                        facts_used=[fact.fact_id],
                        evidence_ids=[fact.evidence.evidence_id],
                        explanation=(
                            f"Contract provides for delayed payment interest ({rate_pct or statutory_min_rate}%). "
                            "Section 16 statutory baseline (3x RBI bank rate with monthly rests) is satisfied or exceeded."
                        ),
                        policy_version=rule_sec16.version if rule_sec16 else "2026.1",
                        statute_ref="MSMED Act 2006, Section 16",
                        severity=Severity.LOW,
                        review_status="approved",
                    )
                )
        return decisions

    def _evaluate_cancellation_fact(
        self, fact: ExtractedFact, eval_date: date
    ) -> List[PolicyDecision]:
        """Evaluates Unilateral Cancellation clause under Contract Act."""
        decisions = []
        val = fact.value
        is_unilateral = val.get("is_unilateral")
        rule_can = self.registry.get_rule("CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION", eval_date)

        if is_unilateral is True:
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-CAN-VIO-{uuid.uuid4().hex[:6]}",
                    policy_id="CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION",
                    decision=DecisionOutcome.TRIGGERED,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation=(
                        "Clause allows unilateral buyer cancellation at sole discretion without reciprocal notice or compensation. "
                        "Potentially unfair or legally reviewable clause under Indian Contract Act 1872 (Sections 23 & 73). "
                        "Final determination requires legal counsel confirmation."
                    ),
                    policy_version=rule_can.version if rule_can else "2026.1",
                    statute_ref="Indian Contract Act 1872, Section 23/73",
                    severity=Severity.MEDIUM,
                    review_status="pending",
                )
            )
        return decisions

    def _evaluate_dispute_fact(
        self, fact: ExtractedFact, eval_date: date
    ) -> List[PolicyDecision]:
        """Evaluates MSMED Act Sec 18 MSEFC statutory jurisdiction vs private arbitration."""
        decisions = []
        val = fact.value
        overrides = val.get("overrides_statutory_council")

        if overrides is True:
            decisions.append(
                PolicyDecision(
                    decision_id=f"DEC-DISP-WRN-{uuid.uuid4().hex[:6]}",
                    policy_id="MSMED_SEC24_OVERRIDING_EFFECT",
                    decision=DecisionOutcome.TRIGGERED,
                    confidence=fact.confidence,
                    facts_used=[fact.fact_id],
                    evidence_ids=[fact.evidence.evidence_id],
                    explanation=(
                        "Arbitration clause purports to govern disputes exclusively without reference to statutory MSEFC council. "
                        "Under Section 18 read with Section 24 of MSMED Act 2006, statutory reference to MSEFC supersedes private arbitration "
                        "for recovery of delayed payments (Silpi Industries v. KSRTC). "
                        "Section 24 applies strictly within Sections 15 to 23 scope and is not a general override for unrelated contractual matters."
                    ),
                    policy_version="2026.1",
                    statute_ref="MSMED Act 2006, Section 18 & 24",
                    severity=Severity.LOW,
                    review_status="pending",
                )
            )
        return decisions
