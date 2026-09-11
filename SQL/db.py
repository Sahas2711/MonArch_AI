import os
import sqlite3
from typing import Optional
from utils.logger import log

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///monarch.db")

_pg_pool = None


async def get_pg_pool():
    """Lazy initialize and return an asyncpg connection pool for Aurora/PostgreSQL."""
    global _pg_pool
    if _pg_pool is None and DATABASE_URL.startswith(("postgresql://", "postgres://")):
        try:
            import asyncpg
            _pg_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
            log.info("Initialized Aurora PostgreSQL connection pool.")
        except Exception as exc:
            log.error("Failed to initialize PostgreSQL pool (%s). Falling back to SQLite.", exc)
    return _pg_pool


def get_sqlite_connection(db_path: str = "monarch.db") -> sqlite3.Connection:
    """Provide a SQLite connection for local development / testing."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db(db_path: str = "monarch.db"):
    """Initialize local SQLite tables corresponding to the Monarch schema."""
    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            source_chat_id TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chat_summaries (
            chat_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            up_to_message_id INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- SaaS Multi-Tenant & Billing Tables (Dev / SQLite)
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free',
            monthly_quota INTEGER NOT NULL DEFAULT 5,
            current_usage INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            billing_email TEXT,
            razorpay_customer_id TEXT
        );

        CREATE TABLE IF NOT EXISTS org_members (
            user_id TEXT NOT NULL,
            org_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, org_id)
        );
        CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members (user_id);

        CREATE TABLE IF NOT EXISTS usage_events (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_usage_org_created ON usage_events (org_id, created_at);

        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            name TEXT NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS plan_limits (
            plan TEXT PRIMARY KEY,
            analyses_per_month INTEGER NOT NULL,
            documents_max INTEGER NOT NULL,
            chat_messages_month INTEGER NOT NULL,
            api_access INTEGER DEFAULT 0
        );

        INSERT OR IGNORE INTO plan_limits (plan, analyses_per_month, documents_max, chat_messages_month, api_access)
        VALUES
            ('free', 5, 10, 100, 0),
            ('pro', 50, 100, 1000, 1),
            ('enterprise', -1, -1, -1, 1);

        CREATE TABLE IF NOT EXISTS analyses_history (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            buyer_name TEXT NOT NULL,
            file_name TEXT,
            compliance_score INTEGER NOT NULL,
            violations_count INTEGER NOT NULL DEFAULT 0,
            report_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_analyses_org_history ON analyses_history (org_id, created_at);
        """
    )
    conn.commit()
    conn.close()
    log.info("Initialized local database schema at %s", db_path)

