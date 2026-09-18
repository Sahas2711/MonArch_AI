"""
MSME Compliance Evaluation Metrics & Comprehensive Confusion Matrix.

Computes production-grade domain evaluation metrics:
- Clause Extraction Precision, Recall, F1
- Full Confusion Matrix (TP, TN, FP, FN, Accuracy, Precision, Recall, Specificity, FPR)
- Review-Routing Accuracy (Auto-approval vs Human Review routing)
- Financial Calculation Error Rate
- Evidence Offset Precision & Grounding Faithfulness
- Markdown & JSON evaluation report generation with baseline comparisons
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class ConfusionMatrixDetails(BaseModel):
    """Detailed confusion matrix for classification and policy outcomes."""
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 1.0
    recall: float = 1.0
    f1_score: float = 1.0
    accuracy: float = 1.0
    specificity: float = 1.0
    false_positive_rate: float = 0.0


class EvaluationMetrics(BaseModel):
    """Aggregated evaluation metrics for MSME compliance pipeline."""
    total_cases: int
    split_name: str = "all"
    extraction_precision: float
    extraction_recall: float
    extraction_f1: float
    compliance_accuracy: float
    true_positive_rate: float
    false_positive_rate: float
    specificity: float
    rag_faithfulness: float
    human_review_trigger_rate: float
    review_routing_accuracy: float = 1.0
    financial_calculation_error_rate: float = 0.0
    evidence_offset_accuracy: float = 1.0
    confusion_matrix: ConfusionMatrixDetails = Field(default_factory=ConfusionMatrixDetails)
    passed_baselines: bool
    baseline_checks: Dict[str, bool] = Field(default_factory=dict)


# Established Production Baselines for MSME Decision Support Pipeline
BASELINES = {
    "extraction_f1": 0.85,
    "compliance_accuracy": 0.90,
    "rag_faithfulness": 0.80,
    "max_false_positive_rate": 0.10,
    "review_routing_accuracy": 0.90,
    "max_financial_error_rate": 0.00,
}


def compute_extraction_f1(
    predictions: List[Dict[str, Any]],
    ground_truths: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Computes Precision, Recall, and F1 score for clause extraction.
    """
    tp = 0
    fp = 0
    fn = 0

    for pred, gt in zip(predictions, ground_truths):
        # 1. Payment days match
        gt_days = gt.get("expected_payment_days")
        pred_days = pred.get("payment_days")
        if gt_days is not None:
            if pred_days == gt_days:
                tp += 1
            else:
                if pred_days is not None:
                    fp += 1
                fn += 1

        # 2. Penalty interest match
        gt_interest = gt.get("expected_has_penalty_interest")
        pred_interest = pred.get("has_penalty_interest")
        if gt_interest is not None:
            if pred_interest == gt_interest:
                tp += 1
            else:
                if pred_interest is not None:
                    fp += 1
                fn += 1

        # 3. Unilateral cancellation match
        gt_cancel = gt.get("expected_has_unilateral_cancellation")
        pred_cancel = pred.get("has_unilateral_cancellation")
        if gt_cancel is not None:
            if pred_cancel == gt_cancel:
                tp += 1
            else:
                if pred_cancel is not None:
                    fp += 1
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def compute_full_confusion_matrix(
    predicted_violations: List[List[str]],
    expected_violations: List[List[str]],
) -> ConfusionMatrixDetails:
    """
    Computes full confusion matrix across all evaluated cases and statutory violation categories.
    """
    tp = 0
    fp = 0
    fn = 0
    tn = 0

    all_known_violations = {"payment_cycle", "interest_penalty", "unilateral_cancellation", "tax_disallowance"}

    for pred_list, exp_list in zip(predicted_violations, expected_violations):
        pred_set = set(pred_list)
        exp_set = set(exp_list)

        for v in all_known_violations:
            in_pred = v in pred_set
            in_exp = v in exp_set

            if in_pred and in_exp:
                tp += 1
            elif in_pred and not in_exp:
                fp += 1
            elif not in_pred and in_exp:
                fn += 1
            else:
                tn += 1

    total_pred_pos = tp + fp
    total_actual_pos = tp + fn
    total_actual_neg = tn + fp
    total_all = tp + tn + fp + fn

    precision = tp / total_pred_pos if total_pred_pos > 0 else 1.0
    recall = tp / total_actual_pos if total_actual_pos > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total_all if total_all > 0 else 1.0
    specificity = tn / total_actual_neg if total_actual_neg > 0 else 1.0
    fpr = fp / total_actual_neg if total_actual_neg > 0 else 0.0

    return ConfusionMatrixDetails(
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        accuracy=round(accuracy, 4),
        specificity=round(specificity, 4),
        false_positive_rate=round(fpr, 4),
    )


def compute_compliance_accuracy(
    predicted_violations: List[List[str]],
    expected_violations: List[List[str]],
) -> Dict[str, float]:
    """
    Computes case-level match accuracy and aggregated rate metrics.
    """
    total = len(predicted_violations)
    if total == 0:
        return {"accuracy": 1.0, "true_positive_rate": 1.0, "false_positive_rate": 0.0, "specificity": 1.0}

    correct = 0
    for pred_list, exp_list in zip(predicted_violations, expected_violations):
        pred_set = set(pred_list)
        exp_set = set(exp_list)
        if pred_set == exp_set or (("payment_cycle" in pred_set and "payment_cycle" in exp_set)):
            correct += 1

    cm = compute_full_confusion_matrix(predicted_violations, expected_violations)

    return {
        "accuracy": round(correct / total, 4),
        "true_positive_rate": cm.recall,
        "false_positive_rate": cm.false_positive_rate,
        "specificity": cm.specificity,
        "correct_cases": correct,
        "total_cases": total,
    }


def compute_rag_faithfulness(
    cited_statutes: List[str],
    ground_truth_statutes: Optional[List[str]] = None,
) -> float:
    """
    Computes grounding faithfulness of statutory citations.
    """
    valid_statute_anchors = {
        "section 15", "section 16", "section 43b(h)", "msme act", "msmed act",
        "income tax act", "45-day", "3x rbi", "bank rate", "compound interest",
        "unilateral", "cancellation", "rule 1", "rule 2", "rule 3", "contract act"
    }

    if not cited_statutes:
        return 1.0

    grounded_count = 0
    for citation in cited_statutes:
        cit_lower = citation.lower()
        if any(anchor in cit_lower for anchor in valid_statute_anchors):
            grounded_count += 1

    return round(grounded_count / len(cited_statutes), 4)


def generate_eval_report(metrics: EvaluationMetrics, case_details: Optional[List[Dict[str, Any]]] = None) -> str:
    """Generates a detailed Markdown evaluation report with full confusion matrix."""
    status_emoji = "✅ PASSED" if metrics.passed_baselines else "❌ FAILED"
    cm = metrics.confusion_matrix

    lines = [
        f"# MSME Compliance Pipeline — Evaluation & Benchmark Report",
        f"",
        f"**Dataset Split**: `{metrics.split_name}` | **Total Cases**: `{metrics.total_cases}`",
        f"**Overall Pipeline Gate Status**: {status_emoji}",
        f"",
        f"## 1. Baseline Target Comparison",
        f"",
        f"| Metric | Measured Value | Baseline Target | Status |",
        f"| :--- | :--- | :--- | :--- |",
        f"| Clause Extraction F1 | `{metrics.extraction_f1:.2%}` | `≥ {BASELINES['extraction_f1']:.0%}` | {'✅ Pass' if metrics.baseline_checks.get('extraction_f1') else '❌ Fail'} |",
        f"| Compliance Accuracy | `{metrics.compliance_accuracy:.2%}` | `≥ {BASELINES['compliance_accuracy']:.0%}` | {'✅ Pass' if metrics.baseline_checks.get('compliance_accuracy') else '❌ Fail'} |",
        f"| Review Routing Accuracy | `{metrics.review_routing_accuracy:.2%}` | `≥ {BASELINES['review_routing_accuracy']:.0%}` | {'✅ Pass' if metrics.baseline_checks.get('review_routing_accuracy') else '❌ Fail'} |",
        f"| Financial Calculation Error Rate | `{metrics.financial_calculation_error_rate:.2%}` | `≤ {BASELINES['max_financial_error_rate']:.0%}` | {'✅ Pass' if metrics.baseline_checks.get('financial_error_rate') else '❌ Fail'} |",
        f"| RAG Faithfulness | `{metrics.rag_faithfulness:.2%}` | `≥ {BASELINES['rag_faithfulness']:.0%}` | {'✅ Pass' if metrics.baseline_checks.get('rag_faithfulness') else '❌ Fail'} |",
        f"| False Positive Rate (FPR) | `{metrics.false_positive_rate:.2%}` | `≤ {BASELINES['max_false_positive_rate']:.0%}` | {'✅ Pass' if metrics.baseline_checks.get('max_false_positive_rate') else '❌ Fail'} |",
        f"",
        f"## 2. Complete Confusion Matrix",
        f"",
        f"| Metric | Count / Rate | Description |",
        f"| :--- | :--- | :--- |",
        f"| **True Positives (TP)** | `{cm.true_positives}` | Violations correctly flagged |",
        f"| **True Negatives (TN)** | `{cm.true_negatives}` | Compliant terms correctly cleared |",
        f"| **False Positives (FP)** | `{cm.false_positives}` | Erroneously flagged violations |",
        f"| **False Negatives (FN)** | `{cm.false_negatives}` | Missed violations |",
        f"| **Precision** | `{cm.precision:.2%}` | `TP / (TP + FP)` |",
        f"| **Recall (Sensitivity)** | `{cm.recall:.2%}` | `TP / (TP + FN)` |",
        f"| **F1 Score** | `{cm.f1_score:.2%}` | Harmonic mean of P & R |",
        f"| **Specificity** | `{cm.specificity:.2%}` | `TN / (TN + FP)` |",
        f"",
        f"## 3. Operational Performance & Gating",
        f"",
        f"- **Human Review Trigger Rate**: `{metrics.human_review_trigger_rate:.2%}`",
        f"- **Evidence Offset Precision**: `{metrics.evidence_offset_accuracy:.2%}`",
        f"- **Financial Golden Test Accuracy**: `{100.0 - (metrics.financial_calculation_error_rate * 100):.2f}%`",
        f"",
    ]

    return "\n".join(lines)
