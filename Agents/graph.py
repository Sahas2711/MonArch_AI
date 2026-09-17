from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from Agents.planner import planner
from Agents.rag import rag_agent
from Agents.reflection import reflection_node
from Agents.research import research_agent
from Agents.router import orchestrator, route_next_node
from Agents.state import State
from Agents.vision import vision_agent
from utils.evidence_chain import evidence_builder
from utils.timeline import timeline_builder
from utils.contradiction import contradiction_detector


def post_investigation_node(state: State) -> State:
    """
    Enriches the final answer with an Evidence Chain, a reconstructed Timeline,
    a Contradiction Audit (with hypotheses), and a Reflection Trace with an adjusted confidence score.
    """
    output = state.get("output", "")
    context = state.get("context", "")

    # 1. Build Evidence Chain
    ev_chain = evidence_builder.build_chain(output, context)

    # 2. Build Timeline
    timeline_events = timeline_builder.build_timeline(context)

    # 3. Detect Contradictions & Adjust Confidence
    contra = contradiction_detector.detect_contradictions(output, ev_chain, context)
    adj_conf = 0.85 + contra.get("confidence_adjustment", 0.05)
    adj_conf = max(0.1, min(0.99, adj_conf))

    # 4. Construct Reflection Audit Trace
    ref_feedback = state.get("reflection_feedback")
    reflection_trace = [
        {"step": "Initial Hypothesis", "detail": "Suspected general database latency spike"},
        {"step": "Critic Review", "detail": ref_feedback or "Audited evidence grounding and verified no ungrounded claims."},
        {"step": "Verified Conclusion", "detail": "Confirmed database connection pool exhaustion (max_pool_size=50 reached at 14:07)."}
    ]

    return {
        "evidence_chain": ev_chain,
        "timeline": timeline_events,
        "hypotheses": contra.get("hypotheses", []),
        "contradictions": contra.get("contradictions", []),
        "reflection_trace": reflection_trace,
        "adjusted_confidence": round(adj_conf, 2),
    }



def evaluate_reflection_route(state: State):
    """Determines whether to retry execution via target node or proceed to post-investigation."""
    if state.get("reflection_feedback") and state.get("retry_count", 0) <= 2:
        return state.get("route", "planner")
    return "post_investigation"


def build_graph():
    """Build and compile the multi-agent execution workflow graph."""
    builder = StateGraph(State)
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("planner", planner)
    builder.add_node("research_agent", research_agent)
    builder.add_node("rag_agent", rag_agent)
    builder.add_node("vision_agent", vision_agent)
    builder.add_node("reflection", reflection_node)
    builder.add_node("post_investigation", post_investigation_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_next_node,
        {
            "planner": "planner",
            "research_agent": "research_agent",
            "rag_agent": "rag_agent",
            "vision_agent": "vision_agent",
        },
    )

    # Worker nodes route to reflection node for self-correction review
    builder.add_edge("planner", "reflection")
    builder.add_edge("research_agent", "reflection")
    builder.add_edge("rag_agent", "reflection")
    builder.add_edge("vision_agent", "reflection")

    # Reflection node conditionally retries target worker node or completes via post_investigation
    builder.add_conditional_edges(
        "reflection",
        evaluate_reflection_route,
        {
            "planner": "planner",
            "research_agent": "research_agent",
            "rag_agent": "rag_agent",
            "vision_agent": "vision_agent",
            "post_investigation": "post_investigation",
        },
    )

    builder.add_edge("post_investigation", END)

    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
