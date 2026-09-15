"""
Statutory Financial Exposure & Compound Interest Calculator.
Implements Section 16 of the MSMED Act 2006:
Compound interest with monthly rests at 3x the RBI bank rate.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class StatutoryInterestResult(BaseModel):
    principal: float
    due_date: date
    payment_date: date
    delay_days: int
    months_overdue: int
    rbi_bank_rate: float
    statutory_rate: float
    monthly_rate: float
    interest_amount: float
    total_recoverable: float
    calculation_method: str = "compound_monthly_rests"


def month_diff(start: date, end: date) -> int:
    """Exact number of complete calendar months between two dates."""
    if end <= start:
        return 0
    diff = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        diff -= 1
    return max(0, diff)


def calculate_statutory_interest(
    principal: float,
    due_date: date,
    payment_date: date,
    rbi_rate: float = 6.5
) -> StatutoryInterestResult:
    """
    Section 16 MSMED Act 2006: compound interest with monthly rests
    at 3x RBI bank rate from due_date to payment_date.
    """
    delay_days = (payment_date - due_date).days if payment_date > due_date else 0
    months_overdue = month_diff(due_date, payment_date)
    # If calendar month diff is 0 but overdue by >= 30 days, count whole 30-day blocks
    if months_overdue == 0 and delay_days >= 30:
        months_overdue = delay_days // 30

    statutory_rate = 3.0 * rbi_rate
    monthly_rate_fraction = statutory_rate / 12.0 / 100.0

    if months_overdue <= 0 or principal <= 0:
        interest = 0.0
    else:
        # Compound interest with monthly rests: P * ((1 + r)^n - 1)
        interest = principal * ((1.0 + monthly_rate_fraction) ** months_overdue - 1.0)

    return StatutoryInterestResult(
        principal=principal,
        due_date=due_date,
        payment_date=payment_date,
        delay_days=delay_days,
        months_overdue=months_overdue,
        rbi_bank_rate=rbi_rate,
        statutory_rate=statutory_rate,
        monthly_rate=round(monthly_rate_fraction * 100, 4),
        interest_amount=round(interest, 2),
        total_recoverable=round(principal + interest, 2),
    )
