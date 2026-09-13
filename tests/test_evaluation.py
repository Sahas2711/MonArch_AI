"""
Tests for MSME Evaluation Framework & Metrics.
"""

import pytest
from evaluation.dataset import EVAL_DATASET
from evaluation.metrics import compute_compliance_accuracy, compute_extraction_f1, compute_rag_faithfulness
from evaluation.runner import run_compliance_eval_async


def test_eval_dataset_size():
    assert len(EVAL_DATASET) >= 30


def test_compute_extraction_f1_perfect():
    preds = [{"payment_days": 90, "has_penalty_interest": False, "has_unilateral_cancellation": None}]
    gts = [{"expected_payment_days": 90, "expected_has_penalty_interest": False, "expected_has_unilateral_cancellation": None}]
    metrics = compute_extraction_f1(preds, gts)
    assert metrics["f1"] == 1.0


def test_compute_compliance_accuracy_perfect():
    pred_v = [["payment_cycle", "tax_disallowance"], ["interest_penalty"]]
    exp_v = [["payment_cycle", "tax_disallowance"], ["interest_penalty"]]
    metrics = compute_compliance_accuracy(pred_v, exp_v)
    assert metrics["accuracy"] == 1.0
    assert metrics["false_positive_rate"] == 0.0


def test_compute_rag_faithfulness():
    citations = [
        "MSME Development Act 2006, Section 15 (Mandatory 45-Day Maximum Cap)",
        "Income Tax Act 1961, Section 43B(h)",
    ]
    faithfulness = compute_rag_faithfulness(citations)
    assert faithfulness == 1.0


@pytest.mark.asyncio
async def test_end_to_end_evaluation_runner():
    metrics = await run_compliance_eval_async()
    assert metrics.total_cases >= 30
    assert metrics.extraction_f1 >= 0.85
    assert metrics.compliance_accuracy >= 0.85
    assert metrics.rag_faithfulness >= 0.80
