"""
Unit tests for Component 4: Statutory Interest & Compound Calculation.
Verifies Section 16 MSMED Act 2006 compound interest with monthly rests at 3x RBI bank rate.
"""

from datetime import date
import pytest
from pipeline.financial import calculate_statutory_interest, month_diff, StatutoryInterestResult


def test_hand_calculated_compound_interest():
    """
    ₹10,00,000 principal, 90 days overdue (3 months), RBI rate 6.5%:
    Statutory rate = 3 * 6.5 = 19.5%
    Monthly rate = 19.5 / 12 / 100 = 0.01625
    Compound interest = 10,00,000 * ((1 + 0.01625)^3 - 1) = ₹49,565.86
    """
    due_date = date(2026, 1, 15)
    payment_date = date(2026, 4, 15)  # exactly 3 calendar months

    res = calculate_statutory_interest(
        principal=1000000.0,
        due_date=due_date,
        payment_date=payment_date,
        rbi_rate=6.5
    )

    assert isinstance(res, StatutoryInterestResult)
    assert res.months_overdue == 3
    assert res.statutory_rate == 19.5
    assert res.monthly_rate == 1.625
    assert res.interest_amount == 49546.48
    assert res.total_recoverable == 1049546.48


def test_zero_delay():
    """Zero months overdue should yield zero interest."""
    d = date(2026, 5, 1)
    res = calculate_statutory_interest(
        principal=500000.0,
        due_date=d,
        payment_date=d,
        rbi_rate=6.5
    )
    assert res.months_overdue == 0
    assert res.interest_amount == 0.0
    assert res.total_recoverable == 500000.0


def test_payment_before_due_date():
    """Payment date before due date should yield zero interest."""
    res = calculate_statutory_interest(
        principal=500000.0,
        due_date=date(2026, 5, 10),
        payment_date=date(2026, 5, 1),
        rbi_rate=6.5
    )
    assert res.months_overdue == 0
    assert res.interest_amount == 0.0
    assert res.total_recoverable == 500000.0


def test_twelve_months_delay():
    """
    12 months delay on ₹1,00,000 at 6.5% RBI (19.5% statutory):
    P * ((1.01625)^12 - 1)
    1.01625^12 ≈ 1.2133887
    Interest ≈ 21338.87
    """
    due_date = date(2025, 1, 1)
    payment_date = date(2026, 1, 1)
    res = calculate_statutory_interest(
        principal=100000.0,
        due_date=due_date,
        payment_date=payment_date,
        rbi_rate=6.5
    )
    assert res.months_overdue == 12
    assert res.interest_amount == 21340.76
    assert res.total_recoverable == 121340.76


def test_month_diff_correctness():
    """Test month_diff under various date scenarios."""
    assert month_diff(date(2026, 1, 15), date(2026, 4, 15)) == 3
    assert month_diff(date(2026, 1, 15), date(2026, 4, 10)) == 2
    assert month_diff(date(2026, 1, 15), date(2026, 4, 20)) == 3
    assert month_diff(date(2025, 10, 1), date(2026, 2, 1)) == 4
    assert month_diff(date(2026, 3, 1), date(2026, 3, 1)) == 0
    assert month_diff(date(2026, 4, 1), date(2026, 3, 1)) == 0
