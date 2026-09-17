"""
Vision Agent Node for Multimodal Image & Document Visual Analysis.
Uses Groq Vision (llama-3.2-11b-vision-preview / llama-3.2-90b-vision-preview) or fallback ChatGroq.
"""

import os
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from Agents.state import State
from utils.config import GROQ_API_KEY
from utils.logger import log
from utils.retry import llm_retry

# Initialize Vision-capable model
VISION_MODEL = os.getenv("VISION_MODEL", "llama-3.2-11b-vision-preview")
vision_llm = ChatGroq(model=VISION_MODEL, api_key=GROQ_API_KEY, timeout=40, max_retries=0)


@llm_retry()
def vision_agent(state: State) -> dict:
    """Vision agent node analyzing image payloads, charts, diagrams, or visual prompts."""
    user_prompt = state["user_inp"]
    image_data = state.get("image_data")

    sys_prompt = (
        "You are an expert multimodal AI vision assistant. Analyze the image or visual document provided "
        "and answer the user's query with extreme detail, precision, and clarity."
    )

    if image_data:
        # Multimodal payload (Text + Base64 Image or URL)
        content_payload = [
            {"type": "text", "text": user_prompt or "Describe and analyze this image in detail."},
            {
                "type": "image_url",
                "image_url": {
                    "url": image_data if image_data.startswith(("http", "data:")) else f"data:image/jpeg;base64,{image_data}"
                },
            },
        ]
        try:
            response = vision_llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=content_payload)])
        except Exception as exc:
            log.warning("Vision model %s failed (%s). Falling back to text response.", VISION_MODEL, exc)
            response = vision_llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)])
    else:
        response = vision_llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)])

    return {
        "output": response.content.strip(),
        "messages": [AIMessage(content=response.content)],
    }
