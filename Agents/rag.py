from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from Agents.state import State
from RAG.manager import rag_manager
from RAG.query_engine import decompose_query, hypothetical_answer, rewrite_query
from utils.config import llm
from utils.retry import llm_retry


@llm_retry()
async def rag_agent(state: State) -> dict:
    """RAG agent node for document retrieval with agentic query decomposition and HyDE."""
    raw_query = state["user_inp"]
    user_id = state.get("user_id")
    feedback = state.get("reflection_feedback")

    # 1. Feedback-driven query rewriting if reflection node requested refinement
    query = await rewrite_query(raw_query, feedback) if feedback else raw_query

    # 2. Multi-hop query decomposition
    sub_queries = await decompose_query(query)

    # 3. Retrieve context across all sub-queries + HyDE hypothetical passage
    retrieved_parts = []
    for sq in sub_queries:
        part = rag_manager.retrieve(sq, user_id=user_id)
        if part and part != "(no relevant context found)":
            retrieved_parts.append(part)

    # HyDE fallback if standard sub-queries yielded nothing
    if not retrieved_parts:
        hypo = await hypothetical_answer(query)
        part = rag_manager.retrieve(hypo, user_id=user_id)
        if part and part != "(no relevant context found)":
            retrieved_parts.append(part)

    context = "\n\n---\n\n".join(retrieved_parts) if retrieved_parts else "(no relevant context found)"

    sys_prompt = (
        "You are an expert document RAG research assistant. Answer the user's question "
        "thoroughly, accurately, and factually using the provided document context below.\n"
        "If the user asks for a summary, overview, or main points of the paper/document, "
        "provide a clear, structured summary of the main contributions, methods, and findings in the context."
    )
    memories = state.get("user_memories")
    if memories:
        sys_prompt += f"\nUser Long-Term Context / Preferences: {', '.join(memories)}"

    response = await llm.ainvoke(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Document Context:\n{context}\n\nUser Question: {query}"),
        ]
    )
    return {
        "output": response.content.strip(),
        "context": context,
        "messages": [AIMessage(content=response.content)],
    }
