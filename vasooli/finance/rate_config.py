"""
RBI Bank Rate Configuration Module.

Maintains current and historical RBI bank rates for MSMED Act Section 16 interest calculations.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from vasooli.domain.models import RateConfig


# Historical & Current RBI Bank Rates table
DEFAULT_RATE_TABLE: List[RateConfig] = [
    RateConfig(
        rbi_bank_rate=Decimal("0.065"),  # 6.50%
        rate_effective_from=date(2023, 2, 8),
        rate_effective_until=None,  # Currently active
        multiplier=3,
        source="RBI Notification - Policy repo rate aligned (6.50%)",
    ),
    RateConfig(
        rbi_bank_rate=Decimal("0.0625"),  # 6.25%
        rate_effective_from=date(2022, 12, 7),
        rate_effective_until=date(2023, 2, 7),
        multiplier=3,
        source="RBI Notification (6.25%)",
    ),
    RateConfig(
        rbi_bank_rate=Decimal("0.059"),  # 5.90%
        rate_effective_from=date(2022, 9, 30),
        rate_effective_until=date(2022, 12, 6),
        multiplier=3,
        source="RBI Notification (5.90%)",
    ),
]


class RateConfigManager:
    """Manages RBI rate lookup based on date."""

    def __init__(self, rate_table: Optional[List[RateConfig]] = None):
        self.rate_table = rate_table or DEFAULT_RATE_TABLE

    def get_rate(self, calculation_date: Optional[date] = None) -> RateConfig:
        """Returns the active RateConfig for the specified calculation date."""
        calc_date = calculation_date or date.today()
        for r in self.rate_table:
            if r.rate_effective_from <= calc_date:
                if r.rate_effective_until is None or calc_date <= r.rate_effective_until:
                    return r
        # Fallback to the latest
        return self.rate_table[0]


def get_current_rate_config(calc_date: Optional[date] = None) -> RateConfig:
    """Convenience helper to retrieve current RateConfig."""
    manager = RateConfigManager()
    return manager.get_rate(calc_date)
