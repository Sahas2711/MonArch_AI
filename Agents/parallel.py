"""
Parallel Multi-Agent Fan-Out & Merger Node for Compound Queries.
Dispatches sub-tasks to Research and RAG agents simultaneously using asyncio.gather().
"""

import asyncio
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from Agents.rag import rag_agent
from Agents.research import research_agent
from Agents.state import State
from utils.config import llm
from utils.logger import log
from utils.retry import llm_retry


@llm_retry()
async def parallel_agent(state: State) -> dict:
    """Dispatches query to Research and RAG nodes concurrently and synthesizes findings."""
    log.info("Parallel Agent Node: Initiating concurrent fan-out (Research + RAG)...")

    # Execute both agents concurrently
    research_task = asyncio.create_task(research_agent(state))
    rag_task = asyncio.create_task(rag_agent(state))

    research_res, rag_res = await asyncio.gather(research_task, rag_task, return_exceptions=True)

    research_out = research_res.get("output", "") if isinstance(research_res, dict) else f"(research error: {research_res})"
    rag_out = rag_res.get("output", "") if isinstance(rag_res, dict) else f"(rag error: {rag_res})"
    context_used = rag_res.get("context", "") if isinstance(rag_res, dict) else ""

    sys_prompt = (
        "You are an executive AI synthesizer. Merge the web research findings and "
        "document RAG findings into a single, cohesive, highly structured response."
    )
    user_payload = (
        f"USER QUERY: {state['user_inp']}\n\n"
        f"--- WEB RESEARCH FINDINGS ---\n{research_out}\n\n"
        f"--- DOCUMENT RAG FINDINGS ---\n{rag_out}"
    )

    merged = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_payload)])
    output_text = merged.content.strip()

    return {
        "output": output_text,
        "context": context_used,
        "parallel_results": {"research": research_out, "rag": rag_out},
        "messages": [AIMessage(content=output_text)],
    }
