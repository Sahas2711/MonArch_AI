"""
MSME Compliance Evaluation Framework.

Provides curated datasets, domain-specific metrics, and an end-to-end
evaluation runner for measuring extraction F1, compliance accuracy,
and RAG faithfulness against established baselines.
"""

from evaluation.dataset import EVAL_DATASET, EvalCase
from evaluation.metrics import (
    compute_compliance_accuracy,
    compute_extraction_f1,
)

__all__ = [
    "EVAL_DATASET",
    "EvalCase",
    "compute_extraction_f1",
    "compute_compliance_accuracy",
]
