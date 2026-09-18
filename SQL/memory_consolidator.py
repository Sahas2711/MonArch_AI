"""
Memory Consolidation & Fact Distillation Engine for Monarch.

Functions:
  - distill_and_store_facts(): Extracts ONLY important durable user facts from conversation history and embeds them into long-term memory.
  - consolidate_chat_history(): Compresses older chat turns into a running summary.
"""

from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from SQL.repository import memory_repo
from utils.config import llm
from utils.logger import log


def distill_and_store_facts(user_id: str, messages: List[dict], chat_id: Optional[str] = None) -> List[str]:
    """
    Extract ONLY important durable user facts (e.g. preferences, role, profile attributes)
    from chat turns and store them as long-term memories.
    """
    if not messages or not user_id:
        return []

    chat_text = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages[-6:])

    prompt = (
        "You are a Memory Distillation Agent. Analyze the recent conversation turns below.\n"
        "Extract ONLY important, durable facts about the user (e.g., job role, technical preferences, "
        "personal details, project goals). Do NOT extract transient conversation chitchat.\n"
        "Return the extracted facts as bullet points (one fact per line). If no important facts exist, reply NONE.\n\n"
        f"Conversation:\n{chat_text}"
    )

    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        lines = [line.strip("- ").strip() for line in response.content.split("\n") if line.strip() and not line.startswith("NONE")]
        
        extracted_facts = []
        for fact in lines:
            if len(fact) > 5 and not fact.upper().startswith("NONE"):
                memory_repo.add_memory(user_id=user_id, content=fact, chat_id=chat_id)
                extracted_facts.append(fact)
                log.info("Distilled & stored durable memory for user %s: %s", user_id, fact)
        return extracted_facts
    except Exception as exc:
        log.warning("Memory distillation failed: %s", exc)
        return []


def consolidate_chat_history(chat_id: str, existing_summary: str, new_messages: List[dict]) -> str:
    """Compress older conversation turns into an updated running summary."""
    if not new_messages:
        return existing_summary

    chat_text = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in new_messages)

    prompt = (
        "Summarize the conversation below into a concise running summary.\n"
        f"Previous Summary:\n{existing_summary or 'None'}\n\n"
        f"New Messages:\n{chat_text}\n\n"
        "Updated Summary:"
    )

    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        updated_summary = response.content.strip()
        log.info("Consolidated chat summary for chat_id %s", chat_id)
        return updated_summary
    except Exception as exc:
        log.warning("Chat consolidation failed: %s", exc)
        return existing_summary
