"""
Deterministic Statutory Interest Calculator.

Implements Section 16 of the MSMED Act, 2006 using exact Decimal arithmetic.

Statutory Formula:
    Compound interest with monthly rests at 3 times the RBI bank rate.
    Compound Interest = P * ((1 + r_monthly)^n - 1)
    Total Recoverable = P + Compound Interest
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import uuid

from vasooli.domain.enums import InterestCalculationMethod
from vasooli.domain.models import FinancialCalculation, RateConfig
from vasooli.finance.rate_config import get_current_rate_config


def month_diff(start: date, end: date) -> int:
    """Exact count of complete calendar months between two dates."""
    if end <= start:
        return 0
    diff = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        diff -= 1
    return max(0, diff)


class StatutoryInterestCalculator:
    """
    Calculates statutory compound interest for MSME delayed payments.
    Uses Decimal arithmetic exclusively to eliminate floating point inaccuracies.
    """

    CALCULATION_VERSION = "interest-2.0.0"

    def calculate(
        self,
        principal: Decimal | str | float,
        delay_start_date: date,
        calculation_date: Optional[date] = None,
        rate_config: Optional[RateConfig] = None,
    ) -> FinancialCalculation:
        """
        Calculates Section 16 MSMED statutory compound interest.
        """
        calc_date = calculation_date or date.today()
        
        # Ensure Decimal
        if isinstance(principal, (str, int)):
            p_dec = Decimal(str(principal))
        elif isinstance(principal, float):
            p_dec = Decimal(str(round(principal, 2)))
        elif isinstance(principal, Decimal):
            p_dec = principal
        else:
            p_dec = Decimal("0.00")

        cfg = rate_config or get_current_rate_config(calc_date)

        delay_days = (calc_date - delay_start_date).days if calc_date > delay_start_date else 0
        months_overdue = month_diff(delay_start_date, calc_date)
        
        # If calendar month diff is 0 but delay >= 30 days, count whole 30-day blocks
        if months_overdue == 0 and delay_days >= 30:
            months_overdue = delay_days // 30

        # Annual statutory rate = rbi_bank_rate * multiplier (e.g. 0.065 * 3 = 0.195)
        annual_rate_dec = cfg.annual_statutory_rate
        # Monthly rate = annual_rate / 12
        monthly_rate_dec = annual_rate_dec / Decimal("12")

        if months_overdue <= 0 or p_dec <= Decimal("0"):
            interest_dec = Decimal("0.00")
        else:
            # Compound interest formula: P * ((1 + r_m)^n - 1)
            one_plus_r = Decimal("1.0") + monthly_rate_dec
            growth_factor = one_plus_r ** months_overdue
            interest_dec = p_dec * (growth_factor - Decimal("1.0"))

        # Round to 2 decimal places with standard HALF_UP rounding
        p_rounded = p_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        interest_rounded = interest_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_rounded = (p_rounded + interest_rounded).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        notes = [
            f"Statutory rate: {cfg.annual_statutory_rate_percent}% p.a. (3x RBI bank rate of {cfg.rbi_bank_rate * 100}%)",
            f"Calculation period: {delay_start_date.isoformat()} to {calc_date.isoformat()} ({delay_days} days, {months_overdue} complete months)",
            f"Compounding: Monthly rests pursuant to Section 16 of the MSMED Act, 2006",
        ]

        return FinancialCalculation(
            calculation_id=f"CALC-{uuid.uuid4().hex[:6]}",
            principal=str(p_rounded),
            delay_start_date=delay_start_date,
            calculation_date=calc_date,
            completed_months=months_overdue,
            annual_rate=str(annual_rate_dec),
            monthly_rate=str(monthly_rate_dec.quantize(Decimal("0.000001"))),
            compound_interest=str(interest_rounded),
            total_recoverable=str(total_rounded),
            calculation_version=self.CALCULATION_VERSION,
            rate_config=cfg,
            method=InterestCalculationMethod.COMPOUND_MONTHLY_RESTS,
            notes=notes,
        )
