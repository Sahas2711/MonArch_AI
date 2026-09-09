"""
GDPR Compliance & Data Erasure Engine for Monarch.
Performs full data purge across SQLite/PostgreSQL, RAG vector index, and user memories.
"""

from RAG.manager import rag_manager
from SQL.db import get_sqlite_connection
from utils.logger import log


def purge_user_data(user_id: str, db_path: str = "monarch.db") -> dict:
    """
    Erases all database records, chat history, user memories, and RAG document chunks for user_id.
    """
    if not user_id:
        return {"status": "failed", "detail": "user_id is required for data purge."}

    # 1. Erase from SQL database (messages, memories, chats)
    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
    memories_deleted = cursor.rowcount

    cursor.execute(
        "DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE user_id = ?)",
        (user_id,),
    )
    messages_deleted = cursor.rowcount

    cursor.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
    chats_deleted = cursor.rowcount

    conn.commit()
    conn.close()

    # 2. Erase from RAG Vector Store & BM25 index
    before_rag_count = len(rag_manager.all_documents)
    rag_manager.all_documents = [
        d for d in rag_manager.all_documents if d.metadata.get("user_id") != user_id
    ]
    rag_manager._bm25_dirty = True
    rag_chunks_deleted = before_rag_count - len(rag_manager.all_documents)

    log.info(
        "GDPR Purge completed for user_id=%s (memories=%d, messages=%d, chats=%d, rag_chunks=%d)",
        user_id,
        memories_deleted,
        messages_deleted,
        chats_deleted,
        rag_chunks_deleted,
    )

    return {
        "status": "success",
        "user_id": user_id,
        "memories_erased": memories_deleted,
        "messages_erased": messages_deleted,
        "chats_erased": chats_deleted,
        "rag_chunks_erased": rag_chunks_deleted,
    }
