from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from Agents.action import action_node
from Agents.fairness import fairness_node
from Agents.planner import planner
from Agents.parallel import parallel_agent
from Agents.rag import rag_agent
from Agents.reflection import reflection_node
from Agents.research import research_agent
from Agents.router import orchestrator, route_next_node
from Agents.state import State
from Agents.vision import vision_agent


def evaluate_reflection_route(state: State):
    """Determines whether to retry execution via target node or finish."""
    if state.get("reflection_feedback") and state.get("retry_count", 0) <= 2:
        return state.get("route", "planner")
    return END


def build_graph():
    """Build and compile the multi-agent execution workflow graph."""
    builder = StateGraph(State)
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("planner", planner)
    builder.add_node("research_agent", research_agent)
    builder.add_node("rag_agent", rag_agent)
    builder.add_node("vision_agent", vision_agent)
    builder.add_node("parallel_agent", parallel_agent)
    builder.add_node("fairness_agent", fairness_node)
    builder.add_node("action_agent", action_node)
    builder.add_node("reflection", reflection_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_next_node,
        {
            "planner": "planner",
            "research_agent": "research_agent",
            "rag_agent": "rag_agent",
            "vision_agent": "vision_agent",
            "parallel_agent": "parallel_agent",
            "fairness_agent": "fairness_agent",
            "action_agent": "action_agent",
        },
    )

    # Fairness node cascades to action node for drafting complaints
    builder.add_edge("fairness_agent", "action_agent")

    # Worker nodes route to reflection node for self-correction review
    builder.add_edge("planner", "reflection")
    builder.add_edge("research_agent", "reflection")
    builder.add_edge("rag_agent", "reflection")
    builder.add_edge("vision_agent", "reflection")
    builder.add_edge("parallel_agent", "reflection")
    builder.add_edge("action_agent", "reflection")

    # Reflection node conditionally retries target worker node or completes
    builder.add_conditional_edges(
        "reflection",
        evaluate_reflection_route,
        {
            "planner": "planner",
            "research_agent": "research_agent",
            "rag_agent": "rag_agent",
            "vision_agent": "vision_agent",
            "parallel_agent": "parallel_agent",
            "fairness_agent": "fairness_agent",
            "action_agent": "action_agent",
            END: END,
        },
    )

    return builder.compile(checkpointer=MemorySaver())


_graph_instance = None


def _get_graph():
    """Return the compiled graph, building it on first call."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


class _LazyGraph:
    """Proxy that defers graph compilation until first attribute access."""

    def __getattr__(self, name):
        return getattr(_get_graph(), name)

    def __call__(self, *args, **kwargs):
        return _get_graph()(*args, **kwargs)

    def __repr__(self):
        if _graph_instance is not None:
            return repr(_graph_instance)
        return "<LazyGraph: not yet compiled>"


graph = _LazyGraph()
