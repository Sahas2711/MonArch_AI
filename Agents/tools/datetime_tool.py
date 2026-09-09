"""
Date and Time Helper Tool for Agents.
"""

from datetime import datetime, timezone
from langchain_core.tools import tool


@tool
def datetime_tool(query: str = "") -> str:
    """Returns the current UTC system date, time, and day of the week."""
    now = datetime.now(timezone.utc)
    return now.strftime("Current UTC Time: %Y-%m-%d %H:%M:%S UTC (%A)")
