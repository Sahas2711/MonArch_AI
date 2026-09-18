-- =====================================================================
-- Migration 002: Vasooli Evidence-First Audit & Determination Tables
-- =====================================================================

-- Evidence items storing exact character offsets and text excerpts
CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id          TEXT PRIMARY KEY,
    document_id          TEXT NOT NULL,
    source_text          TEXT NOT NULL,
    start_char           INTEGER NOT NULL,
    end_char             INTEGER NOT NULL,
    page_number          INTEGER NOT NULL DEFAULT 1,
    clause_reference     TEXT,
    matched_terms        JSONB DEFAULT '[]',
    extraction_method    TEXT DEFAULT 'regex',
    extractor_confidence NUMERIC(4, 3) DEFAULT 0.0,
    created_at           TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_evidence_doc ON evidence_items (document_id);

-- Extracted facts (what the contract says, NOT violations)
CREATE TABLE IF NOT EXISTS extracted_facts (
    fact_id              TEXT PRIMARY KEY,
    document_id          TEXT NOT NULL,
    evidence_id          TEXT NOT NULL REFERENCES evidence_items(evidence_id) ON DELETE CASCADE,
    fact_type            TEXT NOT NULL,
    fact_value           JSONB NOT NULL,
    confidence           NUMERIC(4, 3) DEFAULT 0.0,
    status               TEXT NOT NULL DEFAULT 'definitive',
    inconclusive_reason  TEXT,
    extractor_version    TEXT NOT NULL,
    created_at           TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_facts_doc ON extracted_facts (document_id);

-- Policy decisions (statutory violations and compliance determinations)
CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id          TEXT PRIMARY KEY,
    document_id          TEXT NOT NULL,
    policy_id            TEXT NOT NULL,
    decision_outcome     TEXT NOT NULL, -- TRIGGERED, NOT_TRIGGERED, INCONCLUSIVE
    severity             TEXT NOT NULL DEFAULT 'medium',
    confidence           NUMERIC(4, 3) DEFAULT 0.0,
    facts_used           JSONB DEFAULT '[]',
    evidence_ids         JSONB DEFAULT '[]',
    explanation          TEXT NOT NULL,
    policy_version       TEXT NOT NULL,
    statute_ref          TEXT NOT NULL,
    review_status        TEXT NOT NULL DEFAULT 'pending', -- pending, approved, rejected
    reviewed_by          TEXT,
    reviewed_at          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_decisions_doc ON policy_decisions (document_id);

-- Analysis Reports V2
CREATE TABLE IF NOT EXISTS analyses_v2 (
    analysis_id          TEXT PRIMARY KEY,
    tenant_id            TEXT NOT NULL,
    document_id          TEXT NOT NULL,
    compliance_score     INTEGER NOT NULL,
    risk_level           TEXT NOT NULL,
    recovery_stage       TEXT NOT NULL,
    scorecard_json       JSONB NOT NULL,
    financial_calc_json  JSONB,
    tax_exposure_json    JSONB,
    review_decision_json JSONB,
    pipeline_version     TEXT NOT NULL,
    created_at           TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_analyses_tenant ON analyses_v2 (tenant_id, created_at DESC);

-- Immutable audit events log
CREATE TABLE IF NOT EXISTS audit_events (
    event_id             TEXT PRIMARY KEY,
    tenant_id            TEXT NOT NULL,
    actor_id             TEXT NOT NULL,
    action               TEXT NOT NULL,
    resource_id          TEXT NOT NULL,
    resource_type        TEXT NOT NULL DEFAULT 'contract_analysis',
    details              JSONB NOT NULL,
    timestamp            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit_events (tenant_id, timestamp DESC);
