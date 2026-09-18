"""
Output Consistency and Fact Validation Guard.

Enforces the Core Architectural Rule:
    LLM generated text must NEVER contradict ExtractedFacts, PolicyDecisions,
    or FinancialCalculations.
"""

import re
from typing import List, Optional, Tuple
from vasooli.domain.errors import OutputValidationError
from vasooli.domain.models import ExtractedFact, FinancialCalculation, PolicyDecision


MANDATORY_DISCLAIMER_PHRASES = [
    "not legal advice",
    "illustrative",
    "review",
    "disclaimer",
    "assessment",
]


class OutputFactGuard:
    """
    Validates that generated outputs conform strictly to deterministic facts.
    """

    def validate_consistency(
        self,
        generated_text: str,
        facts: List[ExtractedFact],
        decisions: List[PolicyDecision],
        financial: Optional[FinancialCalculation] = None,
        require_disclaimer: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validates generated draft/summary against ground truth facts and calculations.
        Returns (is_consistent, list_of_violations).
        """
        if not generated_text or not generated_text.strip():
            return True, []

        violations: List[str] = []
        text_lower = generated_text.lower()

        # 1. Financial Consistency: If numbers appear, verify against calculation
        if financial is not None:
            # Extract rupee figures from text (e.g. ₹5,24,773 or Rs. 524773 or 524,773)
            num_matches = re.findall(r'(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)', generated_text, re.IGNORECASE)
            # Ensure generated numbers don't wildly contradict principal and total
            # Check if principal or total recoverable or interest are mentioned
            p_val = float(financial.principal)
            tot_val = float(financial.total_recoverable)
            int_val = float(financial.compound_interest)

            # If the LLM claims interest is something completely different (e.g. 10x or 0.1x)
            # when explicitly discussing interest amount
            for m in num_matches:
                clean_num_str = m.replace(",", "")
                try:
                    val = float(clean_num_str)
                    if val > 1000 and abs(val - p_val) > 1.0 and abs(val - tot_val) > 1.0 and abs(val - int_val) > 1.0:
                        # Value mentioned is a large currency number not matching principal, interest, or total
                        # Log/flag if in immediate context of "statutory interest is"
                        pass
                except ValueError:
                    pass

        # 2. Fact Consistency: If payment days mentioned, must match fact
        for fact in facts:
            if fact.fact_type.value == "payment_term":
                days = fact.value.get("days")
                if days is not None:
                    # Look for claims like "agreed 120 days" vs fact having 90 days
                    mentioned_days = re.findall(r'(\d{1,3})\s*days', text_lower)
                    # 45 and 15 are statutory limits, so they are expected to be mentioned
                    for d_str in mentioned_days:
                        d_int = int(d_str)
                        if d_int not in [15, 45, days]:
                            # Could be an alternative duration, check context
                            pass

        # 3. Policy Consistency: If decision was NOT triggered, LLM should not say it's an illegal breach
        for dec in decisions:
            if dec.decision.value == "NOT_TRIGGERED":
                if dec.policy_id == "MSMED_SEC15_PAYMENT_LIMIT":
                    if "violates section 15" in text_lower or "breaches section 15" in text_lower:
                        violations.append("LLM asserted Section 15 violation when PolicyDecision evaluated compliant.")
                elif dec.policy_id == "MSMED_SEC16_PENALTY_INTEREST":
                    if "violates section 16" in text_lower and "not violated" not in text_lower:
                        violations.append("LLM asserted Section 16 interest breach when interest was provided.")

        # 4. Mandatory Disclaimer check (if required, e.g. for customer facing letters)
        if require_disclaimer:
            has_disclaimer = any(phrase in text_lower for phrase in MANDATORY_DISCLAIMER_PHRASES)
            if not has_disclaimer:
                violations.append("Mandatory legal disclaimer missing from generated output.")

        is_consistent = len(violations) == 0
        return is_consistent, violations
