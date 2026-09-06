"""
Reflection & Self-Correction Node for Monarch Agentic Workflows.

Evaluates assistant generated outputs against original user prompt and context.
Triggers self-correction loops when responses are incomplete, inaccurate, or ungrounded.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from Agents.state import State
from guardrails.output_guard import verify_rag_faithfulness
from utils.config import llm
from utils.logger import log
from utils.retry import llm_retry

MAX_RETRIES = 2


@llm_retry()
def reflection_node(state: State) -> dict:
    """
    Evaluates response quality and checks if self-correction retry is needed.
    """
    user_inp = state["user_inp"]
    output = state.get("output", "")
    context = state.get("context", "")
    route = state.get("route", "")
    current_retries = state.get("retry_count", 0)

    # 1. Output Guardrail check for RAG route
    if route == "rag_agent" and context and context != "(no relevant context found)":
        is_faithful, faith_reason = verify_rag_faithfulness(user_inp, context, output)
        if not is_faithful and current_retries < MAX_RETRIES:
            log.warning("Reflection Node: RAG answer failed faithfulness check. Triggering retry %d.", current_retries + 1)
            return {
                "retry_count": current_retries + 1,
                "reflection_feedback": f"Previous response was not grounded in retrieved documents ({faith_reason}). Re-summarize strictly using the context.",
            }

    # 2. General Quality Reflection Check
    sys_prompt = (
        "You are an expert AI reflection critic evaluating agent output quality.\n"
        "Assess if the GENERATED RESPONSE adequately answers the USER PROMPT.\n"
        "Respond with EXACTLY two lines:\n"
        "LINE 1: PASS or REFINEMENT_NEEDED\n"
        "LINE 2: Feedback description."
    )

    user_payload = f"USER PROMPT: {user_inp}\n\nGENERATED RESPONSE:\n{output}"

    try:
        res = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_payload)])
        content = res.content.strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        verdict = lines[0].upper() if lines else "PASS"
        feedback = lines[1] if len(lines) > 1 else "Response acceptable."

        if "REFINEMENT_NEEDED" in verdict and current_retries < MAX_RETRIES:
            log.info("Reflection Node: Self-correction triggered (%s). Retry count: %d", feedback, current_retries + 1)
            return {
                "retry_count": current_retries + 1,
                "reflection_feedback": f"Refinement feedback: {feedback}",
            }
    except Exception as exc:
        log.warning("Reflection critic check failed (%s). Defaulting to PASS.", exc)

    log.info("Reflection Node passed cleanly for route %s.", route)
    return {
        "reflection_feedback": None,
    }
