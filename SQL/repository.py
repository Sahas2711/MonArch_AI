import sqlite3
import json
import os
from datetime import datetime
from typing import Optional
from utils.logger import log

DB_PATH = os.getenv("SQLITE_DB_PATH", "monarch.db")


class MemoryRepository:
    """SQLite-backed repository for storing agent memory and conversation history."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)
            """)
            conn.commit()

    def store(self, user_id: str, content: str, category: str = "general", metadata: dict = None) -> int:
        """Store a memory entry and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO memories (user_id, category, content, metadata) VALUES (?, ?, ?, ?)",
                (user_id, category, content, json.dumps(metadata or {})),
            )
            conn.commit()
            memory_id = cursor.lastrowid
            log.info("Stored memory %d for user %s (category=%s)", memory_id, user_id, category)
            return memory_id

    def retrieve(self, user_id: str, category: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Retrieve memories for a user, optionally filtered by category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if category:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id = ? AND category = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            return [dict(row) for row in rows]

    def delete(self, memory_id: int) -> bool:
        """Delete a memory entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_users(self) -> list[str]:
        """List all unique user IDs with stored memories."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT user_id FROM memories").fetchall()
            return [row[0] for row in rows]


# Global singleton
memory_repo = MemoryRepository()
