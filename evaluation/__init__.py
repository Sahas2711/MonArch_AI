"""
MSME Compliance Evaluation Framework.

Provides curated datasets, domain-specific metrics, and an end-to-end
evaluation runner for measuring extraction F1, compliance accuracy,
and RAG faithfulness against established baselines.
"""

from evaluation.metrics import (
    compute_compliance_accuracy,
    compute_extraction_f1,
)
from evaluation.runner import run_compliance_eval

__all__ = [
    "compute_extraction_f1",
    "compute_compliance_accuracy",
    "run_compliance_eval",
]
