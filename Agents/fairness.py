from typing import Any, Dict, List
from policy_packs.loader import PolicyPack
from Agents.state import State
from utils.logger import log

try:
    from cedarpy import AuthzResult, is_authorized
    CEDAR_AVAILABLE = True
except ImportError:
    CEDAR_AVAILABLE = False
    log.warning("cedarpy package not found; running fallback Cedar policy evaluator.")


def _evaluate_cedar_rule(entity: Dict[str, Any], rule_type: str) -> bool:
    """Fallback logic mirroring rules.cedar if cedarpy bindings are unavailable."""
    if rule_type == "payment_days":
        return entity.get("paymentDays", 0) > 45
    elif rule_type == "penalty_interest":
        return entity.get("hasPenaltyInterestClause") is False
    elif rule_type == "unilateral_cancellation":
        return entity.get("hasUnilateralCancellation") is True
    return False


async def fairness_node(state: State) -> dict:
    """
    Evaluates extracted clause fields against the active Policy Pack's
    Cedar rules. Runs once per extracted clause. Cedar evaluation is
    synchronous/CPU-bound and fast (no network I/O).
    """
    active_pack = state.get("active_policy_pack") or "msme_payment_terms"
    pack = PolicyPack.load(active_pack)
    extracted_clauses = state.get("extracted_clauses") or []
    violations: List[Dict[str, Any]] = []

    for clause in extracted_clauses:
        clause_id = clause.get("id", "clause_0")
        raw_text = clause.get("raw_text", "")
        payment_days = clause.get("payment_days", 30)
        has_penalty = clause.get("has_penalty_interest", True)
        has_unilateral_cancel = clause.get("has_unilateral_cancellation", False)
        buyer_type = clause.get("buyer_type", "large_enterprise")

        entity = {
            "paymentDays": payment_days,
            "hasPenaltyInterestClause": has_penalty,
            "hasUnilateralCancellation": has_unilateral_cancel,
            "buyerType": buyer_type,
        }

        matched_rules = []
        if CEDAR_AVAILABLE:
            try:
                # Read policy text from rules.cedar
                rules_file = pack.policy_dir / "rules.cedar"
                policies = rules_file.read_text() if rules_file.exists() else ""
                
                # Check authorization
                result = is_authorized(
                    request={"principal": "Evaluation::\"req\"", "action": "Action::\"flag\"", "resource": f"Clause::\"{clause_id}\""},
                    policies=policies,
                    entities=[
                        {
                            "uid": {"type": "Clause", "id": clause_id},
                            "attrs": entity,
                            "parents": []
                        },
                        {
                            "uid": {"type": "Evaluation", "id": "req"},
                            "attrs": {},
                            "parents": []
                        }
                    ]
                )
                if getattr(result, "decision", None) == "ALLOW" or str(getattr(result, "decision", "")).lower() == "allow":
                    matched_rules = getattr(result, "diagnostics", {}).get("reasons", ["msme_rule_violation"])
            except Exception as exc:
                log.warning("Cedarpy authorization call error: %s; falling back to internal evaluator", exc)
                matched_rules = []

        if not matched_rules:
            # Fallback policy rule checks matching rules.cedar
            if _evaluate_cedar_rule(entity, "payment_days"):
                matched_rules.append("Rule 1: Payment cycle exceeds statutory 45-day cap (MSME Act Sec 15)")
            if _evaluate_cedar_rule(entity, "penalty_interest"):
                matched_rules.append("Rule 2: Missing mandatory 3x RBI bank rate compound interest (MSME Act Sec 16)")
            if _evaluate_cedar_rule(entity, "unilateral_cancellation"):
                matched_rules.append("Rule 3: One-sided unilateral cancellation terms detected")

        if matched_rules:
            violations.append({
                "clause_id": clause_id,
                "clause_text": raw_text,
                "matched_rules": matched_rules,
                "cited_law": matched_rules[0] if matched_rules else "MSME Act 2006",
            })

    log.info("Fairness node flagged %d violations across %d clauses", len(violations), len(extracted_clauses))
    return {
        "fairness_violations": violations,
        "route": "fairness_agent",
    }
