from typing import Annotated, Literal, Optional, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Canonical graph state schema shared across all nodes in the workflow."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_inp: str
    user_id: Optional[str]
    image_data: Optional[str]  # Base64 string or image URL
    output: str
    context: str
    route: str
    retry_count: int
    reflection_feedback: Optional[str]
    user_memories: Optional[list[str]]
    parallel_results: Optional[dict]
    extracted_clauses: Optional[list[dict]]
    active_policy_pack: Optional[str]
    fairness_violations: Optional[list[dict]]
    action_drafts: Optional[list[str]]


class RouteDecision(BaseModel):
    """The orchestrator's routing decision, forced into a fixed schema."""

    agent: Literal["planner", "research_agent", "rag_agent", "vision_agent", "parallel_agent", "fairness_agent", "action_agent"] = Field(
        ...,
        description=(
            "planner: general reasoning/drafting with no external info needed. "
            "research_agent: needs live/current web information. "
            "rag_agent: needs the user's own ingested documents. "
            "vision_agent: input contains an image to analyze or visual query. "
            "parallel_agent: compound query requiring both web research and document RAG. "
            "fairness_agent: contract clause compliance analysis against Cedar policy pack."
        ),
    )
    reason: str = Field(..., description="One short sentence justifying the choice.")
