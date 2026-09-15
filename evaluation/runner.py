"""
End-to-End MSME Compliance Evaluation Runner.

Runs the complete 5-stage pipeline across the curated evaluation dataset,
computes domain metrics, validates against established production baselines,
and produces structured evaluation summaries.
"""

from typing import Any, Dict, List, Optional
import asyncio
from evaluation.dataset import EVAL_DATASET, EvalCase
from evaluation.metrics import (
    BASELINES,
    EvaluationMetrics,
    compute_compliance_accuracy,
    compute_extraction_f1,
    compute_rag_faithfulness,
    generate_eval_report,
)
from pipeline.extractor import ClauseExtractor, ExtractedClause
from pipeline.scorer import ComplianceScorer
from pipeline.confidence import ConfidenceGate
from Agents.fairness import fairness_node
from utils.logger import log


async def run_compliance_eval_async(
    dataset: Optional[List[EvalCase]] = None,
    save_report_path: Optional[str] = None,
) -> EvaluationMetrics:
    """
    Asynchronously runs the full compliance pipeline on each test case in dataset.
    Computes all benchmark metrics and checks baseline thresholds.
    """
    cases = dataset or EVAL_DATASET
    extractor = ClauseExtractor()
    scorer = ComplianceScorer()
    gate = ConfidenceGate()

    extraction_preds: List[Dict[str, Any]] = []
    extraction_gts: List[Dict[str, Any]] = []
    predicted_violations_list: List[List[str]] = []
    expected_violations_list: List[List[str]] = []
    all_cited_statutes: List[str] = []
    review_triggers = 0
    case_results: List[Dict[str, Any]] = []

    for case in cases:
        # Stage 1: Extraction
        clauses = extractor.extract_from_text(case.contract_text)
        
        # Consolidate extracted values for metric comparison
        extracted_days = None
        has_penalty_interest = None
        has_unilateral_cancel = None

        for c in clauses:
            if c.payment_days is not None:
                extracted_days = c.payment_days
            if c.has_penalty_interest is not None:
                has_penalty_interest = c.has_penalty_interest
            if c.has_unilateral_cancellation is not None:
                has_unilateral_cancel = c.has_unilateral_cancellation

        extraction_preds.append({
            "payment_days": extracted_days,
            "has_penalty_interest": has_penalty_interest,
            "has_unilateral_cancellation": has_unilateral_cancel,
        })
        extraction_gts.append({
            "expected_payment_days": case.expected_payment_days,
            "expected_has_penalty_interest": case.expected_has_penalty_interest,
            "expected_has_unilateral_cancellation": case.expected_has_unilateral_cancellation,
        })

        # Stage 2: Policy Evaluation (Cedar)
        fairness_state = {
            "extracted_clauses": [
                {
                    "id": c.clause_id,
                    "raw_text": c.raw_text,
                    "payment_days": c.payment_days if c.payment_days is not None else 30,
                    "has_penalty_interest": c.has_penalty_interest if c.has_penalty_interest is not None else True,
                    "has_unilateral_cancellation": c.has_unilateral_cancellation if c.has_unilateral_cancellation is not None else False,
                    "buyer_type": c.buyer_type,
                }
                for c in clauses
            ],
            "active_policy_pack": "msme_payment_terms",
        }
        fairness_res = await fairness_node(fairness_state)
        cedar_violations = fairness_res.get("fairness_violations", [])

        # Build predicted violation type list
        pred_violation_types: List[str] = []
        for cv in cedar_violations:
            for rule in cv.get("matched_rules", []):
                rule_str = str(rule)
                if "Rule 1" in rule_str or "Section 15" in rule_str:
                    pred_violation_types.append("payment_cycle")
                    pred_violation_types.append("tax_disallowance")
                elif "Rule 2" in rule_str or "Section 16" in rule_str:
                    pred_violation_types.append("interest_penalty")
                elif "Rule 3" in rule_str or "unilateral" in rule_str.lower():
                    pred_violation_types.append("unilateral_cancellation")

        pred_violation_types = list(set(pred_violation_types))
        predicted_violations_list.append(pred_violation_types)
        expected_violations_list.append(case.expected_violations)

        for cv in cedar_violations:
            all_cited_statutes.append(cv.get("cited_law", ""))

        # Stage 3: Scoring & Financial Projections
        score_res = scorer.calculate_score(
            violations=[{"violation_type": vt} for vt in pred_violation_types],
            clauses=clauses,
        )

        # Stage 4 & 5: Review Gate
        review_decision = gate.evaluate(clauses=clauses, violations=cedar_violations)
        if review_decision.needs_human_review:
            review_triggers += 1

        case_results.append({
            "case_id": case.id,
            "category": case.category,
            "pred_score": score_res.score,
            "pred_risk": score_res.risk_level,
            "pred_violations": pred_violation_types,
            "exp_violations": case.expected_violations,
            "needs_review": review_decision.needs_human_review,
        })

    # Compute Metrics
    extraction_metrics = compute_extraction_f1(extraction_preds, extraction_gts)
    compliance_metrics = compute_compliance_accuracy(predicted_violations_list, expected_violations_list)
    rag_faithfulness = compute_rag_faithfulness(all_cited_statutes)
    review_trigger_rate = round(review_triggers / len(cases), 4) if cases else 0.0

    # Baseline validation
    f1_val = extraction_metrics["f1"]
    acc_val = compliance_metrics["accuracy"]
    fpr_val = compliance_metrics["false_positive_rate"]

    baseline_checks = {
        "extraction_f1": f1_val >= BASELINES["extraction_f1"],
        "compliance_accuracy": acc_val >= BASELINES["compliance_accuracy"],
        "rag_faithfulness": rag_faithfulness >= BASELINES["rag_faithfulness"],
        "max_false_positive_rate": fpr_val <= BASELINES["max_false_positive_rate"],
    }
    all_passed = all(baseline_checks.values())

    metrics_obj = EvaluationMetrics(
        total_cases=len(cases),
        extraction_precision=extraction_metrics["precision"],
        extraction_recall=extraction_metrics["recall"],
        extraction_f1=f1_val,
        compliance_accuracy=acc_val,
        true_positive_rate=compliance_metrics["true_positive_rate"],
        false_positive_rate=fpr_val,
        specificity=compliance_metrics["specificity"],
        rag_faithfulness=rag_faithfulness,
        human_review_trigger_rate=review_trigger_rate,
        passed_baselines=all_passed,
        baseline_checks=baseline_checks,
    )

    if save_report_path:
        report_md = generate_eval_report(metrics_obj, case_results)
        try:
            with open(save_report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            log.info("Saved evaluation report to %s", save_report_path)
        except Exception as exc:
            log.warning("Could not write eval report: %s", exc)

    log.info(
        "Evaluation finished: Total=%d, F1=%.2f, Acc=%.2f, Faithfulness=%.2f, Passed=%s",
        len(cases), f1_val, acc_val, rag_faithfulness, all_passed
    )

    return metrics_obj


def run_compliance_eval(
    dataset: Optional[List[EvalCase]] = None,
    save_report_path: Optional[str] = None,
) -> EvaluationMetrics:
    """Synchronous entry point for evaluation runner."""
    return asyncio.run(run_compliance_eval_async(dataset=dataset, save_report_path=save_report_path))
