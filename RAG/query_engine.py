"""
Agentic RAG Query Engine.
Provides:
  1. decompose_query() : Multi-hop query decomposition into focused sub-queries.
  2. hypothetical_answer() : HyDE (Hypothetical Document Embeddings) generation.
  3. rewrite_query() : Feedback-driven query rewriting when reflection requests refinement.
"""

from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from utils.config import llm
from utils.logger import log


async def decompose_query(query: str) -> List[str]:
    """Decomposes a complex query into 2-3 sub-queries for multi-hop retrieval."""
    if len(query.split()) < 6:
        return [query]

    sys_prompt = (
        "You are an expert query decomposition assistant for document retrieval.\n"
        "Break down complex user queries into 2-3 distinct, concise sub-queries.\n"
        "Return each sub-query on a new line with no numbering or formatting."
    )
    try:
        res = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=query)])
        sub_queries = [line.strip() for line in res.content.strip().split("\n") if line.strip()]
        if sub_queries:
            log.info("Decomposed query '%s' into: %s", query, sub_queries)
            return sub_queries
    except Exception as exc:
        log.warning("Query decomposition failed (%s); using original query.", exc)

    return [query]


async def hypothetical_answer(query: str) -> str:
    """Generates a hypothetical document passage (HyDE) for embedding retrieval."""
    sys_prompt = (
        "You are a technical document writer. Write a plausible, factual 2-sentence excerpt "
        "or answer passage that would solve the following user query:"
    )
    try:
        res = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=query)])
        hypo = res.content.strip()
        log.info("Generated HyDE passage for query '%s'", query)
        return hypo
    except Exception as exc:
        log.warning("HyDE generation failed (%s).", exc)
        return query


async def rewrite_query(query: str, feedback: Optional[str]) -> str:
    """Rewrites retrieval query based on reflection node feedback."""
    if not feedback:
        return query

    sys_prompt = (
        "You are a search query refiner. Given the ORIGINAL QUERY and REFLECTION FEEDBACK, "
        "output a single improved, search-optimized query string."
    )
    payload = f"ORIGINAL QUERY: {query}\nFEEDBACK: {feedback}"
    try:
        res = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=payload)])
        rewritten = res.content.strip()
        log.info("Rewrote query to: '%s'", rewritten)
        return rewritten
    except Exception as exc:
        log.warning("Query rewrite failed (%s).", exc)
        return query
