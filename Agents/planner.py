from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from Agents.state import State
from utils.config import llm
from utils.retry import llm_retry


@llm_retry()
def planner(state: State) -> dict:
    """Planner node for general reasoning and response generation."""
    sys_prompt = "You are a planning assistant. Give the best, most complete answer to the query."
    response = llm.invoke(
        [SystemMessage(content=sys_prompt), HumanMessage(content=state["user_inp"])]
    )
    return {"output": response.content.strip(), "messages": [AIMessage(content=response.content)]}
