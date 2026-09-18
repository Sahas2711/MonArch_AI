"""
Unit tests for Evaluation Dataset Splits and Confusion Matrix Calculation.
"""

from evaluation.dataset import DatasetSplit, get_dataset_split
from evaluation.metrics import compute_full_confusion_matrix


def test_dataset_splits_exist_and_disjoint():
    dev = get_dataset_split(DatasetSplit.DEV)
    val = get_dataset_split(DatasetSplit.VALIDATION)
    holdout = get_dataset_split(DatasetSplit.HOLDOUT)
    adv = get_dataset_split(DatasetSplit.ADVERSARIAL)

    assert len(dev) == 33
    assert len(val) == 50
    assert len(holdout) == 100
    assert len(adv) == 50

    dev_ids = {c.id for c in dev}
    val_ids = {c.id for c in val}
    holdout_ids = {c.id for c in holdout}
    adv_ids = {c.id for c in adv}

    # Verify no ID collisions across splits
    assert len(dev_ids.intersection(val_ids)) == 0
    assert len(dev_ids.intersection(holdout_ids)) == 0
    assert len(val_ids.intersection(holdout_ids)) == 0
    assert len(adv_ids.intersection(holdout_ids)) == 0


def test_confusion_matrix_calculation():
    preds = [
        ["payment_cycle", "tax_disallowance"],
        ["interest_penalty"],
        [],
    ]
    expected = [
        ["payment_cycle", "tax_disallowance"],
        ["interest_penalty"],
        [],
    ]
    cm = compute_full_confusion_matrix(preds, expected)
    assert cm.true_positives == 3
    assert cm.false_positives == 0
    assert cm.false_negatives == 0
    assert cm.precision == 1.0
    assert cm.recall == 1.0
    assert cm.f1_score == 1.0
