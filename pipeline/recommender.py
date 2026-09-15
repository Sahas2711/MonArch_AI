"""
Decision Recommendation Ladder for MSME Payment Dispute Recovery.
Fixed deterministic if/elif ladder based on contact attempts and escalation timeframe.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class RecommendedAction:
    action_id: str          # "send_demand" | "formal_notice" | "file_samadhaan"
    label: str              # "Send Payment Demand" | "Formal Legal Notice" | "File MSEFC/Samadhaan Complaint"
    effort_level: str       # "low" | "medium" | "high"
    is_recommended: bool
    reason: str             # Explanation for why this action is/is not recommended
    escalation_order: int   # 1, 2, 3


class DecisionRecommender:
    """Evaluates case contact history and recommends the next best recovery action."""

    def recommend(
        self,
        has_violations: bool = True,
        contact_attempts: int = 0,
        first_contact_date: Optional[date] = None,
        current_date: Optional[date] = None,
    ) -> List[RecommendedAction]:
        """
        Decision logic:
        - contact_attempts == 0 -> recommend "Send Payment Demand"
        - contact_attempts > 0 and days_since_first_contact < 30 -> recommend "Formal Legal Notice"
        - contact_attempts > 0 and days_since_first_contact >= 30 -> recommend "File MSEFC/Samadhaan Complaint"
        """
        now = current_date or date.today()
        days_since_first_contact = 0
        if first_contact_date:
            days_since_first_contact = max(0, (now - first_contact_date).days)

        # Determine which action is recommended
        if contact_attempts == 0:
            rec_id = "send_demand"
        elif days_since_first_contact < 30:
            rec_id = "formal_notice"
        else:
            rec_id = "file_samadhaan"

        actions = [
            RecommendedAction(
                action_id="send_demand",
                label="Send Payment Demand",
                effort_level="low",
                is_recommended=(rec_id == "send_demand"),
                reason=(
                    "Recommended because no prior contact has been recorded. "
                    "A polite statutory demand notice establishes the paper trail."
                    if rec_id == "send_demand"
                    else "Initial demand phase completed."
                ),
                escalation_order=1,
            ),
            RecommendedAction(
                action_id="formal_notice",
                label="Formal Legal Notice",
                effort_level="medium",
                is_recommended=(rec_id == "formal_notice"),
                reason=(
                    f"Recommended because {contact_attempts} prior contact attempt(s) made "
                    f"within {days_since_first_contact} days without full resolution. "
                    "Escalate with a formal Section 15/16 legal notice."
                    if rec_id == "formal_notice"
                    else "Previous demand unaddressed or already escalated."
                ),
                escalation_order=2,
            ),
            RecommendedAction(
                action_id="file_samadhaan",
                label="File MSEFC/Samadhaan Complaint",
                effort_level="high",
                is_recommended=(rec_id == "file_samadhaan"),
                reason=(
                    f"Recommended because {days_since_first_contact} days have elapsed since initial contact "
                    f"with {contact_attempts} attempt(s). Exceeds 30-day grace window; "
                    "statutory conciliation via MSME Samadhaan portal is now warranted."
                    if rec_id == "file_samadhaan"
                    else "Filing with MSEFC is the final escalation step once 30-day notice window expires."
                ),
                escalation_order=3,
            ),
        ]

        return actions
