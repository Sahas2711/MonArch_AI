from typing import Any, Dict
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
