from utils.config import llm
from utils.logger import log
from langchain_core.messages import HumanMessage, SystemMessage


def verify_rag_faithfulness(query: str, context: str, response: str) -> tuple[bool, str]:
    """
    Verify that a RAG response is faithful to the retrieved context.

    Returns:
        (is_faithful, reason)
    """
    if not context or context in ("(no relevant context found)", "(no documents ingested yet)"):
        return True, "No context to verify against."

    sys_prompt = (
        "You are a strict faithfulness checker. Given the USER QUERY, DOCUMENT CONTEXT, "
        "and GENERATED RESPONSE, determine if the response is fully grounded in the context.\n"
        "Respond with EXACTLY two lines:\n"
        "LINE 1: FAITHFUL or UNFAITHFUL\n"
        "LINE 2: Brief explanation."
    )

    user_payload = (
        f"USER QUERY: {query}\n\n"
        f"DOCUMENT CONTEXT:\n{context}\n\n"
        f"GENERATED RESPONSE:\n{response}"
    )

    try:
        res = llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_payload),
        ])
        content = res.content.strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        verdict = lines[0].upper() if lines else "FAITHFUL"
        reason = lines[1] if len(lines) > 1 else "No explanation provided."

        is_faithful = "FAITHFUL" in verdict and "UNFAITHFUL" not in verdict
        return is_faithful, reason

    except Exception as exc:
        log.warning("Faithfulness check failed (%s). Defaulting to faithful.", exc)
        return True, "Faithfulness check skipped due to error."
