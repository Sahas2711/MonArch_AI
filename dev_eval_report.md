# MSME Compliance Pipeline — Evaluation & Benchmark Report

**Dataset Split**: `dev` | **Total Cases**: `33`
**Overall Pipeline Gate Status**: ❌ FAILED

## 1. Baseline Target Comparison

| Metric | Measured Value | Baseline Target | Status |
| :--- | :--- | :--- | :--- |
| Clause Extraction F1 | `89.58%` | `≥ 85%` | ✅ Pass |
| Compliance Accuracy | `96.97%` | `≥ 90%` | ✅ Pass |
| Review Routing Accuracy | `84.85%` | `≥ 90%` | ❌ Fail |
| Financial Calculation Error Rate | `0.00%` | `≤ 0%` | ✅ Pass |
| RAG Faithfulness | `100.00%` | `≥ 80%` | ✅ Pass |
| False Positive Rate (FPR) | `0.00%` | `≤ 10%` | ✅ Pass |

## 2. Complete Confusion Matrix

| Metric | Count / Rate | Description |
| :--- | :--- | :--- |
| **True Positives (TP)** | `42` | Violations correctly flagged |
| **True Negatives (TN)** | `88` | Compliant terms correctly cleared |
| **False Positives (FP)** | `0` | Erroneously flagged violations |
| **False Negatives (FN)** | `2` | Missed violations |
| **Precision** | `100.00%` | `TP / (TP + FP)` |
| **Recall (Sensitivity)** | `95.45%` | `TP / (TP + FN)` |
| **F1 Score** | `97.67%` | Harmonic mean of P & R |
| **Specificity** | `100.00%` | `TN / (TN + FP)` |

## 3. Operational Performance & Gating

- **Human Review Trigger Rate**: `30.30%`
- **Evidence Offset Precision**: `100.00%`
- **Financial Golden Test Accuracy**: `100.00%`
