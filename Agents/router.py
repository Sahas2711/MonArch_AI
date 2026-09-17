from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from Agents.state import RouteDecision, State
from utils.config import llm
from utils.logger import log
from utils.retry import llm_retry

from RAG.manager import rag_manager

from guardrails.input_guard import sanitize_and_validate_input

router_llm = llm.with_structured_output(RouteDecision)


@llm_retry()
def _route_decision(user_inp: str) -> RouteDecision:
    has_rag_docs = len(rag_manager.all_documents) > 1 or any("Monarch RAG baseline" not in d.page_content for d in rag_manager.all_documents)
    query_lower = user_inp.lower()
    
    rag_keywords = {"paper", "reserch", "research", "document", "pdf", "file", "ingested", "uploaded", "article", "report", "summary"}
    
    # Deterministic RAG route override if RAG corpus contains documents
    if has_rag_docs and any(kw in query_lower for kw in rag_keywords):
        log.info("Direct RAG route override triggered for query: %r", user_inp)
        return RouteDecision(agent="rag_agent", reason="Target query matched active RAG document corpus.")

    rag_instruction = (
        "NOTE: User HAS uploaded/ingested documents into the RAG vector store. "
        "If the user asks about 'the paper', 'the document', 'the PDF', 'the file', 'that I ingested', "
        "'research paper', 'what is it about', or asks questions about uploaded content, YOU MUST SELECT rag_agent."
        if has_rag_docs
        else "Only pick rag_agent if the request explicitly refers to uploaded documents or private files."
    )

    sys_prompt = (
        "You are a routing controller for a multi-agent system. Given the user's "
        "message, decide which single agent should handle it.\n"
        f"{rag_instruction}\n"
        "Only pick research_agent if the request clearly needs current/live external web information "
        "(news, prices, weather, recent events).\n"
        "Otherwise pick planner for general reasoning, coding, or writing tasks."
    )
    try:
        return router_llm.invoke(
            [SystemMessage(content=sys_prompt), HumanMessage(content=user_inp)]
        )
    except Exception as exc:
        log.warning("Router LLM call failed (%s). Falling back to rule-based agent routing.", exc)
        if has_rag_docs:
            return RouteDecision(agent="rag_agent", reason="Fallback rule: Target query matched active RAG document corpus.")
        return RouteDecision(agent="planner", reason="Fallback rule: Defaulting to general reasoning planner agent.")



def orchestrator(state: State) -> dict:
    raw_input = state["user_inp"]
    sanitized_input, is_safe, reason = sanitize_and_validate_input(raw_input)

    if not is_safe:
        log.warning("Orchestrator blocked query via Input Guardrail: %s", reason)
        return {
            "route": "planner",
            "output": f"⚠️ Request Blocked by Guardrail: {reason}",
            "user_inp": sanitized_input,
        }

    if state.get("image_data"):
        log.info("Direct Vision route override triggered (image payload attached).")
        return {"route": "vision_agent", "user_inp": sanitized_input}

    decision = _route_decision(sanitized_input)
    log.info("Routing decision: %s (%s)", decision.agent, decision.reason)
    return {"route": decision.agent, "user_inp": sanitized_input}


def route_next_node(state: State) -> Literal["planner", "research_agent", "rag_agent", "vision_agent"]:
    return state["route"]  # type: ignore[return-value]
