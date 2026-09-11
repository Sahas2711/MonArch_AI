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

-- =====================================================================
-- SAAS MULTI-TENANT & BILLING EXTENSIONS (Vasooli / Wemboo)
-- =====================================================================

-- ORGANIZATIONS (the billing/tenant entity)
CREATE TABLE IF NOT EXISTS organizations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT NOT NULL,
    plan                 TEXT NOT NULL DEFAULT 'free'
                         CHECK (plan IN ('free', 'pro', 'enterprise')),
    monthly_quota        INTEGER NOT NULL DEFAULT 5,
    current_usage        INTEGER NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ DEFAULT now(),
    billing_email        TEXT,
    razorpay_customer_id TEXT
);

-- ORG MEMBERS (links users to orgs — org_id derived from JWT, never client input)
CREATE TABLE IF NOT EXISTS org_members (
    user_id   TEXT        NOT NULL,   -- Cognito sub / username claim
    org_id    UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role      TEXT        NOT NULL DEFAULT 'member'
              CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, org_id)
);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members (user_id);

-- USAGE METERING
CREATE TABLE IF NOT EXISTS usage_events (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id    TEXT        NOT NULL,
    event_type TEXT        NOT NULL CHECK (event_type IN ('analysis','ingest','chat')),
    tokens_used INTEGER   DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_usage_org_created ON usage_events (org_id, created_at DESC);

-- API KEYS
CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    key_hash     TEXT        UNIQUE NOT NULL,
    key_prefix   TEXT        NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    is_active    BOOLEAN     DEFAULT true
);

-- PLAN LIMITS (seed data)
CREATE TABLE IF NOT EXISTS plan_limits (
    plan                TEXT    PRIMARY KEY,
    analyses_per_month  INTEGER NOT NULL,   -- -1 = unlimited
    documents_max       INTEGER NOT NULL,
    chat_messages_month INTEGER NOT NULL,
    api_access          BOOLEAN DEFAULT false
);

INSERT INTO plan_limits (plan, analyses_per_month, documents_max, chat_messages_month, api_access)
VALUES
    ('free',        5,   10,   100, false),
    ('pro',        50,  100,  1000, true),
    ('enterprise', -1,   -1,    -1, true)
ON CONFLICT (plan) DO NOTHING;

-- CONTRACT AUDIT & ANALYSIS REPORTS
CREATE TABLE IF NOT EXISTS analyses_history (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id            TEXT NOT NULL,
    buyer_name         TEXT NOT NULL,
    file_name          TEXT,
    compliance_score   INTEGER NOT NULL,
    violations_count   INTEGER NOT NULL DEFAULT 0,
    report_data        JSONB NOT NULL,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_analyses_org ON analyses_history (org_id, created_at DESC);
