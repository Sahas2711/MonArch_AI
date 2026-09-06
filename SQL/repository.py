import uuid
from typing import List, Optional
from SQL.db import get_sqlite_connection, init_sqlite_db


class MemoryRepository:
    """Repository managing long-term user memories and chat persistent storage."""

    def __init__(self, db_path: str = "monarch.db"):
        self.db_path = db_path
        init_sqlite_db(db_path)

    def add_memory(self, user_id: str, content: str, chat_id: Optional[str] = None) -> str:
        """Store a new long-term memory fact for a user."""
        memory_id = str(uuid.uuid4())
        conn = get_sqlite_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_memories (id, user_id, content, source_chat_id, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (memory_id, user_id, content, chat_id),
        )
        conn.commit()
        conn.close()
        return memory_id

    def get_user_memories(self, user_id: str) -> List[str]:
        """Fetch all active long-term memories for a given user."""
        conn = get_sqlite_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM user_memories WHERE user_id = ? AND is_active = 1",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [row["content"] for row in rows]

    def save_message(self, chat_id: str, role: str, content: str) -> int:
        """Save a user/assistant message to history."""
        conn = get_sqlite_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.commit()
        msg_id = cursor.lastrowid
        conn.close()
        return msg_id


memory_repo = MemoryRepository()
