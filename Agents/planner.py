from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from Agents.state import State
from Agents.tools import calculator_tool, datetime_tool, search_memories_tool, code_executor_tool
from utils.config import llm
from utils.retry import llm_retry

PLANNER_TOOLS = [calculator_tool, datetime_tool, search_memories_tool, code_executor_tool]
_planner_llm = llm.bind_tools(PLANNER_TOOLS)


@llm_retry()
async def planner(state: State) -> dict:
    """Multi-step tool-use planner node with ReAct capabilities."""
    sys_prompt = (
        "You are an expert multi-step reasoning and planning assistant. "
        "Use available tools when mathematical calculation, date/time lookup, memory search, or Python code execution is needed."
    )
    memories = state.get("user_memories")
    if memories:
        sys_prompt += f"\nUser Long-Term Context / Preferences: {', '.join(memories)}"

    user_inp = state["user_inp"]
    messages = [SystemMessage(content=sys_prompt), HumanMessage(content=user_inp)]

    response = await _planner_llm.ainvoke(messages)

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_map = {t.name: t for t in PLANNER_TOOLS}
        for call in response.tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            if tool_name in tool_map:
                tool_output = await tool_map[tool_name].ainvoke(tool_args)
                messages.append(response)
                messages.append(HumanMessage(content=f"[Tool Output from {tool_name}]: {tool_output}"))
        response = await llm.ainvoke(messages)

    return {"output": response.content.strip(), "messages": [AIMessage(content=response.content)]}
