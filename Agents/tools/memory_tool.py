"""
User Long-Term Memory Tool for Searching & Storing Facts.
"""

from typing import Optional
from langchain_core.tools import tool
from SQL.repository import memory_repo


@tool
def search_memories_tool(user_id: str) -> str:
    """Searches active long-term facts and user preferences stored for a given user_id."""
    if not user_id:
        return "No user_id provided to query memories."
    memories = memory_repo.get_user_memories(user_id)
    if not memories:
        return f"No active memories found for user '{user_id}'."
    return f"Active User Memories for '{user_id}':\n" + "\n".join(f"- {m}" for m in memories)


@tool
def add_memory_tool(user_id: str, fact: str) -> str:
    """Saves a new long-term fact or preference for a user into persistent memory."""
    if not user_id or not fact:
        return "Both user_id and fact content are required to store a memory."
    mem_id = memory_repo.add_memory(user_id=user_id, content=fact)
    return f"Successfully stored user memory [id={mem_id}]: '{fact}'"
