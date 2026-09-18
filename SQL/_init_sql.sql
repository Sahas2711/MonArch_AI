-- =====================================================================
-- FULL SCHEMA: RAG + Dual-Layer Memory (Short-term + Long-term)
-- Single Postgres database using the pgvector extension.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. EXTENSION
-- ---------------------------------------------------------------------
-- pgvector adds a native VECTOR column type + similarity search operators
-- (<->  euclidean, <#>  inner product, <=>  cosine distance).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- for gen_random_uuid()


-- ---------------------------------------------------------------------
-- 1. CORE ENTITIES (users, chats)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chats (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Every message in every conversation. This is your source of truth —
-- Redis (short-term cache) is just a fast read-through layer on top of this.
CREATE TABLE messages (
    id            BIGSERIAL PRIMARY KEY,
    chat_id       UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role          TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content       TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_messages_chat ON messages (chat_id, created_at);


-- ---------------------------------------------------------------------
-- 2. RAG: KNOWLEDGE BASE (documents you feed the system, not user memory)
-- ---------------------------------------------------------------------
CREATE TABLE documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title         TEXT NOT NULL,
    source_uri    TEXT,               -- file path / URL it came from
    uploaded_at   TIMESTAMPTZ DEFAULT now()
);

-- Each document is split into chunks before embedding, since embedding
-- models have a token limit and retrieval works best on small,
-- semantically coherent pieces of text.
CREATE TABLE knowledge_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,       -- order within the doc, for context stitching
    chunk_text    TEXT NOT NULL,
    embedding     VECTOR(1536),       -- dimension must match your embedding model
    metadata      JSONB DEFAULT '{}'  -- e.g. {"page": 4, "section": "Intro"}
);

-- ivfflat = an approximate-nearest-neighbor index. "lists" controls the
-- number of clusters; rule of thumb: lists ≈ sqrt(row_count).
-- Needs ANALYZE after bulk insert for the planner to use it well.
CREATE INDEX idx_chunks_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);


-- ---------------------------------------------------------------------
-- 3. LONG-TERM MEMORY: durable facts about a user, persists across chats
-- ---------------------------------------------------------------------
CREATE TABLE user_memories (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content            TEXT NOT NULL,       -- the extracted fact, plain text
    embedding          VECTOR(1536),
    source_chat_id     UUID REFERENCES chats(id),
    is_active          BOOLEAN DEFAULT true, -- soft-delete: never hard-delete facts
    created_at         TIMESTAMPTZ DEFAULT now(),
    last_confirmed_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memories_embedding
    ON user_memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Partial index: most queries filter to one user's ACTIVE memories only,
-- so index just that slice instead of the whole table.
CREATE INDEX idx_memories_active_user
    ON user_memories (user_id) WHERE is_active;


-- ---------------------------------------------------------------------
-- 4. SHORT-TERM MEMORY: rolling summary of the CURRENT chat
-- ---------------------------------------------------------------------
-- Raw messages table (above) already holds full history. This table
-- holds a compressed running summary so you don't have to re-send
-- the entire message table to the LLM every turn once a chat gets long.
CREATE TABLE chat_summaries (
    chat_id        UUID PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
    summary        TEXT NOT NULL,
    up_to_message_id BIGINT NOT NULL,  -- last message included in this summary
    updated_at     TIMESTAMPTZ DEFAULT now()
);


-- =====================================================================
-- 5. EXAMPLE QUERIES
-- =====================================================================

-- (a) RAG retrieval: top-5 relevant chunks for a query embedding
-- SELECT chunk_text, metadata
-- FROM knowledge_chunks
-- ORDER BY embedding <=> :query_embedding
-- LIMIT 5;

-- (b) Long-term memory retrieval: top-5 relevant facts for THIS user
-- SELECT content
-- FROM user_memories
-- WHERE user_id = :user_id AND is_active
-- ORDER BY embedding <=> :query_embedding
-- LIMIT 5;

-- (c) De-duplication check before inserting a new memory:
-- if the closest existing memory is too similar, UPDATE instead of INSERT
-- SELECT id, content, 1 - (embedding <=> :new_embedding) AS similarity
-- FROM user_memories
-- WHERE user_id = :user_id AND is_active
-- ORDER BY embedding <=> :new_embedding
-- LIMIT 1;
-- -- if similarity > 0.92 → UPDATE that row's content/embedding/last_confirmed_at
-- -- else → INSERT new row

-- (d) Soft-delete / supersede an outdated memory instead of hard delete
-- UPDATE user_memories SET is_active = false WHERE id = :old_memory_id;