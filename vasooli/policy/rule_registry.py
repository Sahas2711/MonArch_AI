"""
Policy Rule Registry Module.

Stores, manages, and resolves versioned legal policy rules for MSME compliance checking.
"""

from datetime import date
from typing import Dict, List, Optional
from vasooli.domain.models import PolicyRule


class PolicyRegistry:
    """
    In-memory registry of versioned policy rules.
    Allows point-in-time rule resolution based on contract execution date.
    """

    def __init__(self):
        self._rules: Dict[str, List[PolicyRule]] = {}

    def register(self, rule: PolicyRule) -> None:
        """Registers a policy rule version."""
        if rule.policy_id not in self._rules:
            self._rules[rule.policy_id] = []
        # Keep sorted by effective_from descending
        self._rules[rule.policy_id].append(rule)
        self._rules[rule.policy_id].sort(key=lambda r: r.effective_from, reverse=True)

    def get_rule(self, policy_id: str, evaluation_date: Optional[date] = None) -> Optional[PolicyRule]:
        """
        Retrieves the active rule version for a given date (defaults to today).
        """
        eval_date = evaluation_date or date.today()
        versions = self._rules.get(policy_id, [])
        for version in versions:
            if version.effective_from <= eval_date:
                if version.effective_until is None or eval_date <= version.effective_until:
                    return version
        return versions[0] if versions else None

    def list_rules(self, evaluation_date: Optional[date] = None) -> List[PolicyRule]:
        """Lists all active rules for the given date."""
        active_rules = []
        for policy_id in self._rules:
            rule = self.get_rule(policy_id, evaluation_date)
            if rule:
                active_rules.append(rule)
        return active_rules

    def count(self) -> int:
        return len(self._rules)
