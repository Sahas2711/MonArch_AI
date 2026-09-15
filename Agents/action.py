from typing import Any, Dict, Optional
from Agents.state import State
from utils.config import llm
from utils.logger import log

try:
    from strands import Agent, tool
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False
    log.warning("strands-agents package not found; running fallback action agent.")


if STRANDS_AVAILABLE:
    @tool
    def draft_samadhaan_complaint(violation_text: str, cited_law: str) -> str:
        """Strands tool: drafts a Samadhaan-portal-ready complaint paragraph."""
        return (
            f"FORM 1 — APPLICATION UNDER SECTION 18 OF MSMED ACT 2006\n"
            f"Grounds: {violation_text}\n"
            f"Statutory Basis: {cited_law}\n"
            f"Demand is hereby made for immediate payment of outstanding principal together with "
            f"compound interest at three times (3x) the RBI Bank Rate."
        )

    try:
        strands_action_agent = Agent(
            tools=[draft_samadhaan_complaint],
            model="bedrock/claude",
        )
    except Exception as exc:
        log.warning("Could not initialize Strands agent (%s); using fallback LLM execution", exc)
        strands_action_agent = None
else:
    strands_action_agent = None


# Deterministic statutory fallbacks for pre-signature negotiation
DEFAULT_COMPLIANT_CLAUSES: Dict[str, tuple] = {
    "payment_cycle": (
        "Payments for goods or services delivered shall be made within forty-five (45) days from the date of acceptance, "
        "in strict accordance with Section 15 of the Micro, Small and Medium Enterprises Development (MSMED) Act, 2006.",
        "Clauses extending payment periods beyond 45 days violate Section 15 of the MSMED Act and trigger mandatory compound interest penalties.",
    ),
    "interest_penalty": (
        "In the event of delayed payment beyond 45 days, the buyer shall pay compound interest with monthly rests "
        "at three times (3x) the RBI bank rate from the appointed day until full discharge, pursuant to Section 16 of the MSMED Act, 2006.",
        "Waiving interest on delayed payments strips the statutory financial deterrent guaranteed under Section 16 of the MSMED Act.",
    ),
    "unilateral_cancellation": (
        "Either party may terminate this agreement only upon thirty (30) days prior written notice, subject to full compensation "
        "for work performed and direct costs incurred up to the date of termination.",
        "Unilateral cancellation without notice or compensation transfers all operational and material risk to the MSME supplier.",
    ),
}


async def negotiate_clause(
    clause_text: str,
    violation_type: str,
    cited_law: str = "MSMED Act 2006",
    fallback_replacement: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pre-signature negotiation advisor.
    Rewrites an offending contractual clause into an MSME-compliant version with plain-language risk explanation.
    """
    # Look up deterministic default
    default_entry = DEFAULT_COMPLIANT_CLAUSES.get(
        violation_type,
        (
            fallback_replacement or f"The terms shall comply with mandatory protections under {cited_law}.",
            f"The clause conflicts with {cited_law} and imposes unfair commercial risk on the supplier.",
        ),
    )
    compliant_rep = fallback_replacement or default_entry[0]
    risk_exp = default_entry[1]

    prompt = (
        f"You are reviewing a contract clause BEFORE signing. Rewrite this clause to be MSME-compliant.\n"
        f"Original clause: {clause_text}\n"
        f"Violation: {violation_type} under {cited_law}\n\n"
        f"Provide:\n"
        f"1) The compliant replacement clause\n"
        f"2) One sentence explaining why the original is risky."
    )

    if strands_action_agent:
        try:
            res = await strands_action_agent.invoke_async(prompt)
            text_out = str(res)
            if "replacement" in text_out.lower() or len(text_out) > 30:
                compliant_rep = text_out.strip()
        except Exception as exc:
            log.warning("Strands negotiate_clause failed (%s); trying fallback LLM", exc)

    if not strands_action_agent and llm:
        try:
            res = await llm.ainvoke(prompt)
            content = res.content.strip()
            if content and len(content) > 30:
                # If LLM returned both parts, keep the formatted text
                compliant_rep = content
        except Exception as exc:
            log.debug("Direct LLM negotiation rewrite fallback used default: %s", exc)

    return {
        "original_clause": clause_text,
        "violation_type": violation_type,
        "cited_law": cited_law,
        "compliant_replacement": compliant_rep,
        "risk_explanation": risk_exp,
        "confidence": 0.90,
    }


async def action_node(state: State) -> dict:
    """
    LangGraph-compatible wrapper around a Strands agent or fallback LLM call.
    Keeps the node signature identical to every other node in Agents/,
    so router.py and graph.py need minimal changes to call it.
    """
    violations = state.get("fairness_violations") or []
    drafts = []

    for violation in violations:
        clause_text = violation.get("clause_text", "")
        cited_law = violation.get("cited_law", "MSME Development Act 2006")

        prompt = (
            f"Draft a formal Samadhaan portal complaint paragraph under Section 18 of MSMED Act 2006 "
            f"for the following violation:\nClause: {clause_text}\nCited Law: {cited_law}"
        )

        draft_content = ""
        if strands_action_agent:
            try:
                result = await strands_action_agent.invoke_async(prompt)
                draft_content = str(result)
            except Exception as exc:
                log.warning("Strands invoke_async failed (%s); falling back to default LLM", exc)
                draft_content = ""

        if not draft_content:
            # Fallback direct LLM execution
            try:
                response = await llm.ainvoke(prompt)
                draft_content = response.content.strip()
            except Exception as exc:
                log.error("Fallback LLM action drafting failed: %s", exc)
                draft_content = (
                    f"FORM 1 COMPLAINT DRAFT:\n"
                    f"Clause: {clause_text}\n"
                    f"Statute: {cited_law}\n"
                    f"Grounds: Mandatory 45-day payment cap and statutory compound interest violated."
                )

        drafts.append(draft_content)

    log.info("Action node generated %d complaint drafts", len(drafts))
    return {
        "action_drafts": drafts,
        "output": "\n\n---\n\n".join(drafts) if drafts else "No violations requiring action drafts.",
        "route": "action_agent",
    }
