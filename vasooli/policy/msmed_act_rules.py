"""
MSMED Act 2006 Statutory Policy Rules.

Defines the canonical legal rules under the Micro, Small and Medium Enterprises
Development Act, 2006, Income Tax Act 1961 Section 43B(h), and Indian Contract Act 1872.
"""

from datetime import date
from vasooli.domain.models import PolicyRule
from vasooli.policy.rule_registry import PolicyRegistry


# 1. Section 15: Maximum 45 days payment timeline with written agreement
MSMED_SEC15_PAYMENT_LIMIT = PolicyRule(
    policy_id="MSMED_SEC15_PAYMENT_LIMIT",
    statute="MSMED Act 2006",
    section="15",
    version="2026.1",
    effective_from=date(2006, 10, 2),
    rule_type="payment_period",
    parameters={
        "max_agreed_days": 45,
        "default_statutory_days": 15,
        "buyer_types": ["large_enterprise", "public_sector", "msme"],
        "requires_written_agreement": True,
    },
    description=(
        "Under Section 15 of MSMED Act 2006, where buyer and seller agree in writing, "
        "the payment period shall not exceed 45 days from the day of acceptance or deemed acceptance. "
        "Clauses delaying the trigger beyond statutory acceptance are non-compliant."
    ),
)

# 1b. Section 15: 15-day timeline in the absence of written agreement
MSMED_SEC15_NO_AGREEMENT = PolicyRule(
    policy_id="MSMED_SEC15_NO_AGREEMENT",
    statute="MSMED Act 2006",
    section="15",
    version="2026.1",
    effective_from=date(2006, 10, 2),
    rule_type="payment_period",
    parameters={
        "max_statutory_days": 15,
        "requires_written_agreement": False,
    },
    description=(
        "Under Section 15 of MSMED Act 2006, in the absence of an agreement in writing, "
        "payment must be made within 15 days from the day of acceptance or deemed acceptance."
    ),
)

# 2. Section 16: Mandatory 3x RBI Bank Rate Compound Interest
MSMED_SEC16_PENALTY_INTEREST = PolicyRule(
    policy_id="MSMED_SEC16_PENALTY_INTEREST",
    statute="MSMED Act 2006",
    section="16",
    version="2026.1",
    effective_from=date(2006, 10, 2),
    rule_type="interest_rate",
    parameters={
        "statutory_multiplier": 3,
        "compounding_frequency": "monthly",
        "waiver_permitted": False,
    },
    description=(
        "Under Section 16 of MSMED Act 2006, where buyer fails to pay within the Section 15 period, "
        "the buyer is liable to pay compound interest with monthly rests at three times the bank rate "
        "notified by the Reserve Bank of India. Any contractual term waiving or diminishing this right is void."
    ),
)

# 3. Section 24: Overriding Effect (Non-obstante Clause for Sec 15-23)
MSMED_SEC24_OVERRIDING_EFFECT = PolicyRule(
    policy_id="MSMED_SEC24_OVERRIDING_EFFECT",
    statute="MSMED Act 2006",
    section="24",
    version="2026.1",
    effective_from=date(2006, 10, 2),
    rule_type="statutory_override",
    parameters={
        "overrides_conflicting_contracts": True,
        "statutory_scope": ["15", "16", "17", "18", "19", "20", "21", "22", "23"],
    },
    description=(
        "Section 24 provides that provisions of Sections 15 to 23 shall have effect "
        "notwithstanding anything inconsistent therewith contained in any other law or agreement. "
        "This applies specifically to MSMED statutory recovery and MSEFC jurisdiction, not as a general override for all contractual disputes."
    ),
)

# 4. Income Tax Act Section 43B(h): Disallowance of overdue MSME deductions
IT_ACT_SEC43BH_DISALLOWANCE = PolicyRule(
    policy_id="IT_ACT_SEC43BH_DISALLOWANCE",
    statute="Income Tax Act 1961",
    section="43B(h)",
    version="2024.1",
    effective_from=date(2024, 4, 1),
    rule_type="tax_disallowance",
    parameters={
        "disallowance_trigger_days_agreed": 45,
        "disallowance_trigger_days_default": 15,
        "financial_year_cutoff": True,
        "is_illustrative": True,
    },
    description=(
        "Under Section 43B(h) of the Income Tax Act 1961 (w.e.f. Assessment Year 2024-25), "
        "any sum payable by an assessee to a micro or small enterprise beyond the time limit specified "
        "in Section 15 of the MSMED Act 2006 shall be allowed as a deduction only in the previous year "
        "in which such sum is actually paid. Tax impact amounts are estimated potential exposures based on configured assumptions."
    ),
)

# 5. Contract Act Section 23 / 73 Unilateral Cancellation
CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION = PolicyRule(
    policy_id="CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION",
    statute="Indian Contract Act 1872",
    section="23/73",
    version="2026.1",
    effective_from=date(1872, 9, 1),
    rule_type="cancellation",
    parameters={
        "requires_bilateral_notice": True,
        "requires_reviewer_confirmation": True,
    },
    description=(
        "A clause granting one party unilateral discretion to terminate or cancel orders without "
        "compensating for work executed or without reasonable notice is potentially unfair or legally reviewable "
        "under commercial fairness and damages principles (Indian Contract Act 1872, Sections 23 & 73)."
    ),
)


def create_default_policy_registry() -> PolicyRegistry:
    """Instantiates and populates the canonical MSME policy registry."""
    registry = PolicyRegistry()
    registry.register(MSMED_SEC15_PAYMENT_LIMIT)
    registry.register(MSMED_SEC15_NO_AGREEMENT)
    registry.register(MSMED_SEC16_PENALTY_INTEREST)
    registry.register(MSMED_SEC24_OVERRIDING_EFFECT)
    registry.register(IT_ACT_SEC43BH_DISALLOWANCE)
    registry.register(CONTRACT_ACT_SEC23_UNILATERAL_CANCELLATION)
    return registry
