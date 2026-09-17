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
    reflection_trace: Optional[list]
    evidence_chain: list
    timeline: list
    hypotheses: list
    contradictions: list
    adjusted_confidence: float




class RouteDecision(BaseModel):
    """The orchestrator's routing decision, forced into a fixed schema."""

    agent: Literal["planner", "research_agent", "rag_agent", "vision_agent"] = Field(
        ...,
        description=(
            "planner: general reasoning/drafting with no external info needed. "
            "research_agent: needs live/current web information. "
            "rag_agent: needs the user's own ingested documents. "
            "vision_agent: input contains an image to analyze or visual query."
        ),
    )
    reason: str = Field(..., description="One short sentence justifying the choice.")
