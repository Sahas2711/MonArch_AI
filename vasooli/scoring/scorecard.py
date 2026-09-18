"""
Compliance Scorecard Generator Module.

Builds a transparent, multi-dimensional ComplianceScorecard from PolicyDecisions
and ExtractedFacts without conflating compliance score, financial exposure,
and confidence metrics into a single arbitrary number.
"""

from typing import List, Optional
from vasooli.domain.enums import DecisionOutcome, RecoveryStage, Severity
from vasooli.domain.models import (
    ComplianceScorecard,
    ExtractedFact,
    FinancialCalculation,
    PolicyDecision,
    ScoreFactor,
    TaxExposureEstimate,
)


class ComplianceScorer:
    """
    Computes deterministic compliance scores based on policy outcomes.
    """

    SCORER_VERSION = "compliance-score-2.0.0"

    # Deduction point rules
    DECISION_DEDUCTIONS = {
        "MSMED_SEC15_PAYMENT_LIMIT": 30,
        "MSMED_SEC16_PENALTY_INTEREST": 25,
        "CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION": 20,
        "IT_ACT_SEC43BH_DISALLOWANCE": 15,
        "MSMED_SEC24_OVERRIDING_EFFECT": 10,
    }

    def compute_scorecard(
        self,
        decisions: List[PolicyDecision],
        facts: List[ExtractedFact],
        financial_exposure: Optional[FinancialCalculation] = None,
        tax_exposure: Optional[TaxExposureEstimate] = None,
    ) -> ComplianceScorecard:
        """
        Computes the complete ComplianceScorecard.
        """
        base_score = 100
        total_deduction = 0
        factors: List[ScoreFactor] = []

        for dec in decisions:
            is_triggered = dec.decision == DecisionOutcome.TRIGGERED
            is_ambiguous = dec.decision == DecisionOutcome.INCONCLUSIVE
            
            pts = self.DECISION_DEDUCTIONS.get(dec.policy_id, 15)
            
            if is_triggered:
                deduction = pts
                total_deduction += deduction
                factors.append(
                    ScoreFactor(
                        rule=dec.policy_id.lower(),
                        points=-deduction,
                        severity=dec.severity,
                        evidence_ids=dec.evidence_ids,
                        policy_id=dec.policy_id,
                        triggered=True,
                        rationale=dec.explanation,
                    )
                )
            elif is_ambiguous:
                deduction = pts // 2
                total_deduction += deduction
                factors.append(
                    ScoreFactor(
                        rule=f"{dec.policy_id.lower()}_ambiguous",
                        points=-deduction,
                        severity=Severity.MEDIUM,
                        evidence_ids=dec.evidence_ids,
                        policy_id=dec.policy_id,
                        triggered=True,
                        rationale=f"Ambiguity flagged: {dec.explanation}",
                    )
                )
            else:
                factors.append(
                    ScoreFactor(
                        rule=dec.policy_id.lower(),
                        points=0,
                        severity=Severity.LOW,
                        evidence_ids=dec.evidence_ids,
                        policy_id=dec.policy_id,
                        triggered=False,
                        rationale=dec.explanation,
                    )
                )

        final_score = max(0, min(100, base_score - total_deduction))

        # Determine risk level
        if final_score >= 85:
            risk_level = "low"
        elif final_score >= 65:
            risk_level = "medium"
        elif final_score >= 40:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Calculate category-specific calibrated confidence (eliminating simple average masking)
        payment_term_confs = [f.confidence for f in facts if f.fact_type == FactType.PAYMENT_TERM]
        date_resolution_confs = [
            0.40 if f.status in (FactStatus.AMBIGUOUS, FactStatus.INCONCLUSIVE) else f.confidence
            for f in facts if f.fact_type == FactType.PAYMENT_TERM
        ]
        policy_match_confs = [d.confidence for d in decisions]
        financial_confs = [1.0] if financial_exposure is not None else [0.95]

        pay_conf = min(payment_term_confs) if payment_term_confs else 0.50
        date_conf = min(date_resolution_confs) if date_resolution_confs else 0.50
        pol_conf = min(policy_match_confs) if policy_match_confs else 0.50
        fin_conf = min(financial_confs)

        min_conf = min(pay_conf, date_conf, pol_conf, fin_conf)
        # Weighted composite confidence
        composite_conf = round(
            0.35 * pay_conf + 0.25 * date_conf + 0.25 * pol_conf + 0.15 * fin_conf, 3
        )

        cat_confidence = CategoryConfidence(
            payment_term_confidence=round(pay_conf, 3),
            date_resolution_confidence=round(date_conf, 3),
            policy_match_confidence=round(pol_conf, 3),
            financial_input_confidence=round(fin_conf, 3),
            min_confidence=round(min_conf, 3),
        )

        # Determine recovery stage
        if final_score < 40 or (financial_exposure and int(float(financial_exposure.compound_interest)) > 50000):
            recovery_stage = RecoveryStage.SAMADHAAN_FILING
        elif final_score < 65:
            recovery_stage = RecoveryStage.LEGAL_NOTICE
        elif final_score < 85:
            recovery_stage = RecoveryStage.DEMAND
        else:
            recovery_stage = RecoveryStage.PREVENTIVE_REVISE

        return ComplianceScorecard(
            base_score=base_score,
            final_score=final_score,
            risk_level=risk_level,
            factors=factors,
            financial_exposure=financial_exposure,
            tax_exposure=tax_exposure,
            confidence_score=composite_conf,
            category_confidence=cat_confidence,
            recovery_stage=recovery_stage,
            score_version=self.SCORER_VERSION,
        )
