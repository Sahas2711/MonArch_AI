"""
Vasooli Core Pipeline Orchestrator.

Executes the deterministic, evidence-first contract compliance pipeline:
    Input Validation → Fact Extraction → Policy Evaluation → Financial Calculation →
    Tax Exposure → Scorecard Generation → Human Review Routing → Counter-Clause Drafting →
    Output Consistency Validation → Audit Logging → Persistence.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from vasooli.domain.enums import FactStatus, RecoveryStage, ReviewRouting, Severity
from vasooli.domain.models import (
    AnalysisReportV2,
    BuildMetadata,
    ComplianceScorecard,
    ExtractedFact,
    FinancialCalculation,
    PolicyDecision,
    ReviewDecision,
    TaxExposureEstimate,
)
from vasooli.extraction.fact_extractor import FactExtractor
from vasooli.finance.interest import StatutoryInterestCalculator
from vasooli.finance.tax_exposure import estimate_section_43bh_tax_exposure
from vasooli.persistence.audit import AuditTrailManager
from vasooli.persistence.repository import VasooliRepository
from vasooli.policy.evaluator import PolicyEvaluator
from vasooli.scoring.scorecard import ComplianceScorer
from vasooli.security.output_guard import OutputFactGuard
from vasooli.security.prompt_guard import PromptGuard


class VasooliOrchestrator:
    """
    Main orchestration engine executing the 10-stage deterministic compliance pipeline.
    """

    PIPELINE_VERSION = "2.0.0"

    def __init__(
        self,
        repository: Optional[VasooliRepository] = None,
        audit_manager: Optional[AuditTrailManager] = None,
    ):
        self.prompt_guard = PromptGuard()
        self.fact_extractor = FactExtractor()
        self.policy_evaluator = PolicyEvaluator()
        self.interest_calculator = StatutoryInterestCalculator()
        self.compliance_scorer = ComplianceScorer()
        self.output_guard = OutputFactGuard()
        self.repository = repository or VasooliRepository()
        self.audit_manager = audit_manager or AuditTrailManager()

    def analyze_contract(
        self,
        contract_text: str,
        buyer_name: str = "Enterprise Buyer",
        file_name: str = "Contract Agreement",
        contract_value: Optional[float] = None,
        delay_start_date: Optional[date] = None,
        actor_id: str = "system",
        org_id: str = "ORG-DEFAULT",
    ) -> AnalysisReportV2:
        """
        Runs the complete deterministic compliance analysis.
        """
        document_id = f"DOC-{uuid.uuid4().hex[:8]}"
        report_id = f"REP-{uuid.uuid4().hex[:8]}"

        # 1. Input Guardrail
        sanitized_text, _, _ = self.prompt_guard.validate_and_sanitize(contract_text, mask_personal_data=False)

        # 2. Fact Extraction
        facts: List[ExtractedFact] = self.fact_extractor.extract_facts(
            document_text=sanitized_text,
            document_id=document_id,
            contract_value=contract_value,
        )

        # 3. Policy Evaluation
        decisions: List[PolicyDecision] = self.policy_evaluator.evaluate(facts)

        # Extract values for financial calculations
        principal_val = contract_value or 500000.0  # Default illustrative value if not specified
        calc_start = delay_start_date or (date.today() - timedelta(days=90))

        # 4. Financial Calculation (Section 16 Compound Interest)
        financial_calc: FinancialCalculation = self.interest_calculator.calculate(
            principal=Decimal(str(principal_val)),
            delay_start_date=calc_start,
            calculation_date=date.today(),
        )

        # 5. Tax Exposure Estimation (Section 43B(h))
        tax_exposure: TaxExposureEstimate = estimate_section_43bh_tax_exposure(
            invoice_amount=Decimal(str(principal_val)),
        )

        # 6. Scorecard Generation
        scorecard: ComplianceScorecard = self.compliance_scorer.compute_scorecard(
            decisions=decisions,
            facts=facts,
            financial_exposure=financial_calc,
            tax_exposure=tax_exposure,
        )

        # 7. Human Review Decision Routing
        review_decision = self._route_review(facts, decisions, scorecard)

        # 8. Counter-Clause Drafting & Summary Generation (Deterministic templates with exact statutory anchors)
        summary_text, counter_clauses, samadhaan_draft = self._generate_prescriptive_actions(
            facts, decisions, scorecard, financial_calc, buyer_name
        )

        # 9. Output Consistency Guardrail
        is_consistent, violations = self.output_guard.validate_consistency(
            generated_text=summary_text,
            facts=facts,
            decisions=decisions,
            financial=financial_calc,
        )

        # 10. Assemble Report
        report = AnalysisReportV2(
            report_id=report_id,
            report_version=1,
            document_id=document_id,
            buyer_name=buyer_name,
            file_name=file_name,
            extracted_facts=facts,
            policy_decisions=decisions,
            financial_calculation=financial_calc,
            tax_exposure=tax_exposure,
            scorecard=scorecard,
            review_decision=review_decision,
            review_status="approved" if review_decision.auto_approved else "pending",
            overall_summary=summary_text,
            draft_counter_clauses=counter_clauses,
            draft_samadhaan_complaint=samadhaan_draft,
            analyzed_at=datetime.utcnow(),
            build_metadata=BuildMetadata(
                version=self.PIPELINE_VERSION,
                commit_sha="v2.0-deterministic",
                policy_pack_version="msmed-2026.01",
                extractor_version=self.fact_extractor.EXTRACTOR_VERSION,
                calculation_version=self.interest_calculator.CALCULATION_VERSION,
                build_timestamp=datetime.utcnow().isoformat(),
            ),
        )

        # 11. Record Audit Event
        self.audit_manager.record_event(
            event_type="analysis_created",
            actor_id=actor_id,
            resource_id=report_id,
            changes={
                "score": scorecard.final_score,
                "risk_level": scorecard.risk_level,
                "decisions_count": len(decisions),
                "facts_count": len(facts),
                "needs_review": review_decision.needs_human_review,
            },
        )

        # 12. Save to Repository
        self.repository.save_analysis_report(report)

        return report

    def _route_review(
        self,
        facts: List[ExtractedFact],
        decisions: List[PolicyDecision],
        scorecard: ComplianceScorecard,
    ) -> ReviewDecision:
        """Determines if the report requires human review or qualifies for auto-approval."""
        review_reasons = []
        flags = []

        # Check for ambiguous or low confidence facts
        for f in facts:
            if f.status == FactStatus.AMBIGUOUS:
                review_reasons.append(f"Ambiguous fact detected: {f.fact_type.value}")
                flags.append(f.inconclusive_reason or "Ambiguous trigger")
            elif f.confidence < 0.70:
                review_reasons.append(f"Low extraction confidence on {f.fact_type.value} ({f.confidence})")

        # Check for high severity decisions
        high_sev = any(d.severity == Severity.CRITICAL or (d.severity == Severity.HIGH and d.decision.value == "TRIGGERED") for d in decisions)
        if high_sev:
            review_reasons.append("High or Critical statutory violations identified.")

        if scorecard.final_score < 60:
            review_reasons.append(f"Critical compliance risk score ({scorecard.final_score}/100)")

        needs_review = len(review_reasons) > 0
        auto_approved = not needs_review and scorecard.confidence_score >= 0.85

        return ReviewDecision(
            needs_human_review=needs_review,
            review_reasons=review_reasons,
            confidence_score=scorecard.confidence_score,
            auto_approved=auto_approved,
            flags=flags,
            recommended_action=ReviewRouting.AUTO_APPROVE if auto_approved else ReviewRouting.HUMAN_REVIEW,
        )

    def _generate_prescriptive_actions(
        self,
        facts: List[ExtractedFact],
        decisions: List[PolicyDecision],
        scorecard: ComplianceScorecard,
        financial: FinancialCalculation,
        buyer_name: str,
    ) -> Tuple[str, List[Dict[str, str]], Optional[str]]:
        """Generates evidence-anchored summary, counter clauses, and Samadhaan petition draft."""
        triggered_decisions = [d for d in decisions if d.decision.value == "TRIGGERED"]
        
        summary_lines = [
            f"Contract Compliance Analysis for {buyer_name}:",
            f"- Compliance Score: {scorecard.final_score}/100 ({scorecard.risk_level.upper()} RISK)",
            f"- Statutory Interest Exposure: ₹{financial.compound_interest} (Total Recoverable: ₹{financial.total_recoverable})",
            f"- Flagged Violations: {len(triggered_decisions)} statutory breaches identified.",
        ]
        for d in triggered_decisions:
            summary_lines.append(f"  • {d.statute_ref}: {d.explanation}")

        counter_clauses = []
        # Counter-clause for Section 15 Payment Terms
        if any(d.policy_id == "MSMED_SEC15_PAYMENT_LIMIT" and d.decision.value == "TRIGGERED" for d in decisions):
            counter_clauses.append({
                "clause_type": "Payment Terms",
                "issue": "Payment period exceeds Section 15 45-day statutory ceiling.",
                "proposed_clause": (
                    "Payment shall be made within forty-five (45) calendar days from the date of delivery or deemed acceptance "
                    "in accordance with Section 15 of the Micro, Small and Medium Enterprises Development (MSMED) Act, 2006."
                ),
                "legal_rationale": "Aligns contractual payment terms strictly with Section 15 mandatory timeline.",
            })

        # Counter-clause for Section 16 Interest Penalty
        if any(d.policy_id == "MSMED_SEC16_PENALTY_INTEREST" and d.decision.value == "TRIGGERED" for d in decisions):
            counter_clauses.append({
                "clause_type": "Interest on Delayed Payment",
                "issue": "Contract attempts to waive statutory interest or omits mandatory delayed payment interest.",
                "proposed_clause": (
                    "In the event of delay in payment beyond the agreed period, Buyer shall be liable to pay compound interest "
                    "with monthly rests at three times (3x) the Reserve Bank of India bank rate from the appointed day until full settlement, "
                    "pursuant to Section 16 of the MSMED Act, 2006."
                ),
                "legal_rationale": "Enforces non-waivable statutory interest rights under MSMED Act Sections 16 & 24.",
            })

        # Counter-clause for Unilateral Cancellation
        if any(d.policy_id == "CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION" and d.decision.value == "TRIGGERED" for d in decisions):
            counter_clauses.append({
                "clause_type": "Termination and Order Cancellation",
                "issue": "Unilateral buyer cancellation without compensation.",
                "proposed_clause": (
                    "Either party may terminate this agreement upon thirty (30) days prior written notice. In the event of buyer cancellation, "
                    "the buyer shall compensate the supplier for all raw materials procured, works in progress, and delivered milestones up to the date of notice."
                ),
                "legal_rationale": "Ensures bilateral commercial fairness and prevents uncompensated manufacturing loss under Indian Contract Act Section 73.",
            })

        # Samadhaan petition draft if recovery stage warrants it
        samadhaan_draft = None
        if scorecard.recovery_stage in [RecoveryStage.SAMADHAAN_FILING, RecoveryStage.LEGAL_NOTICE]:
            samadhaan_draft = (
                f"APPLICATION BEFORE THE MICRO AND SMALL ENTERPRISES FACILITATION COUNCIL (MSEFC)\n"
                f"UNDER SECTION 18 OF THE MSMED ACT, 2006\n\n"
                f"CLAIMANT: MSME Supplier\n"
                f"RESPONDENT: {buyer_name}\n\n"
                f"1. Principal Amount Overdue: ₹{financial.principal}\n"
                f"2. Statutory Compound Interest (Sec 16): ₹{financial.compound_interest}\n"
                f"3. Total Amount Claimed: ₹{financial.total_recoverable}\n"
                f"4. Period of Overdue: {financial.completed_months} months from {financial.delay_start_date}\n\n"
                f"PRAYER:\n"
                f"The Claimant prays that the Hon'ble Facilitation Council issue directions under Section 18 of the MSMED Act, 2006 "
                f"directing the Respondent to pay the outstanding total sum of ₹{financial.total_recoverable} along with compound interest "
                f"with monthly rests at 3x the RBI bank rate until realization."
            )

        return "\n".join(summary_lines), counter_clauses, samadhaan_draft
