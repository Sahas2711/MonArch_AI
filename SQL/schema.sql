-- =====================================================================
-- MONARCH DATABASE SCHEMA: RAG + Short-Term & Long-Term Memory
-- Compatible with PostgreSQL + pgvector extension
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Core Entities
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chats (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id            BIGSERIAL PRIMARY KEY,
    chat_id       UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role          TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content       TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages (chat_id, created_at);

-- Knowledge Base Documents
CREATE TABLE IF NOT EXISTS documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title         TEXT NOT NULL,
    source_uri    TEXT,
    uploaded_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    chunk_text    TEXT NOT NULL,
    embedding     VECTOR(1536),
    metadata      JSONB DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Long-Term User Memories
CREATE TABLE IF NOT EXISTS user_memories (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content            TEXT NOT NULL,
    embedding          VECTOR(1536),
    source_chat_id     UUID REFERENCES chats(id),
    is_active          BOOLEAN DEFAULT true,
    created_at         TIMESTAMPTZ DEFAULT now(),
    last_confirmed_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memories_embedding
    ON user_memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memories_active_user
    ON user_memories (user_id) WHERE is_active;

-- Short-Term Chat Summaries
CREATE TABLE IF NOT EXISTS chat_summaries (
    chat_id        UUID PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
    summary        TEXT NOT NULL,
    up_to_message_id BIGINT NOT NULL,
    updated_at     TIMESTAMPTZ DEFAULT now()
);
