"""Multi-agent orchestration system (LangGraph state, nodes, router, workflow graph)."""
from Agents.state import State, RouteDecision


def build_graph():
    """Lazy accessor – imports the real builder only when called."""
    from Agents.graph import build_graph as _build
    return _build()


def get_graph():
    """Lazy accessor – imports the compiled graph only when called."""
    from Agents.graph import graph as _graph
    return _graph


__all__ = ["State", "RouteDecision", "build_graph", "get_graph"]

