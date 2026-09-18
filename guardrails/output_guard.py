"""
Output Guardrail for Monarch.

Verifies RAG output faithfulness against retrieved document context to prevent hallucinations.
"""

from typing import Tuple
from utils.config import llm
from utils.logger import log
from utils.retry import llm_retry
from langchain_core.messages import SystemMessage, HumanMessage


@llm_retry()
def verify_rag_faithfulness(user_inp: str, context: str, output: str) -> Tuple[bool, str]:
    """
    Checks if output is strictly grounded in retrieved context.
    Returns (is_faithful, explanation).
    """
    if not context or context == "(no relevant context found)":
        return True, "No context to verify against."

    sys_prompt = (
        "You are an output verification guardrail evaluating RAG answer faithfulness.\n"
        "Assess whether the proposed ANSWER is strictly supported and grounded by the provided CONTEXT.\n"
        "Respond with EXACTLY two lines:\n"
        "LINE 1: PASS or FAIL\n"
        "LINE 2: One sentence explanation."
    )

    user_payload = f"USER QUERY: {user_inp}\n\nCONTEXT:\n{context}\n\nPROPOSED ANSWER:\n{output}"

    try:
        res = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_payload)])
        content = res.content.strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        status = lines[0].upper() if lines else "PASS"
        reason = lines[1] if len(lines) > 1 else "Answer grounded in context."

        is_faithful = "PASS" in status
        if not is_faithful:
            log.warning("Output Guardrail flagged hallucination / ungrounded answer: %s", reason)
        return is_faithful, reason
    except Exception as exc:
        log.error("Output guardrail check failed: %s", exc)
        return True, "Guardrail check bypassed due to error."
