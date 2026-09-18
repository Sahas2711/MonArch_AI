from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from Agents.state import State
from RAG.manager import rag_manager
from utils.config import llm
from utils.retry import llm_retry


@llm_retry()
def rag_agent(state: State) -> dict:
    """RAG agent node for document retrieval and context-based answering."""
    query = state["user_inp"]
    context = rag_manager.retrieve(query, user_id=state.get("user_id"))

    sys_prompt = (
        "You are an expert document RAG research assistant. Answer the user's question "
        "thoroughly, accurately, and factually using the provided document context below.\n"
        "If the user asks for a summary, overview, or main points of the paper/document, "
        "provide a clear, structured summary of the main contributions, methods, and findings in the context."
    )
    response = llm.invoke(
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
