"""
Section 43B(h) Tax Exposure Estimator.

Calculates estimated buyer tax impact when payments to MSMEs are delayed past
Section 15 limits under Section 43B(h) of the Income Tax Act, 1961.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from vasooli.domain.models import TaxExposureEstimate


DEFAULT_CORPORATE_TAX_RATE = Decimal("0.25")  # 25.0%


def estimate_section_43bh_tax_exposure(
    invoice_amount: Decimal | str | float,
    corporate_tax_rate: Optional[Decimal | str | float] = None,
    assessment_year: str = "AY 2025-26",
    buyer_qualifies: bool = True,
    payment_qualifies: bool = True,
) -> TaxExposureEstimate:
    """
    Estimates illustrative tax impact for disallowed business deduction.
    
    Tax Exposure = Invoice Amount * Assumed Corporate Tax Rate
    """
    if isinstance(invoice_amount, (str, int)):
        amt = Decimal(str(invoice_amount))
    elif isinstance(invoice_amount, float):
        amt = Decimal(str(round(invoice_amount, 2)))
    elif isinstance(invoice_amount, Decimal):
        amt = invoice_amount
    else:
        amt = Decimal("0.00")

    if corporate_tax_rate is None:
        rate = DEFAULT_CORPORATE_TAX_RATE
    elif isinstance(corporate_tax_rate, (str, int, float)):
        rate = Decimal(str(corporate_tax_rate))
    else:
        rate = corporate_tax_rate

    tax_impact = (amt * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return TaxExposureEstimate(
        estimated_tax_impact=str(tax_impact),
        assumed_tax_rate=str(rate),
        buyer_qualifies=buyer_qualifies,
        payment_qualifies=payment_qualifies,
        applicable_assessment_year=assessment_year,
        is_illustrative=True,
        disclaimer=(
            "This is an illustrative estimate of potential tax disallowance under Section 43B(h) of the "
            "Income Tax Act, 1961. Actual liability depends on the buyer's applicable corporate/firm tax slab, "
            "surcharge, cess, and whether the payment was cleared prior to filing the return of income."
        ),
    )
