"""
Database Repository and Schema for Vasooli V2.

Provides durable SQLite persistence for AnalysisReportV2, ExtractedFact,
PolicyDecision, EvidenceItem, and AuditEvent entities with explicit transaction
rollbacks, duplicate prevention, and multi-tenant isolation.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional
from vasooli.domain.errors import DuplicateReportError, PersistenceError
from vasooli.domain.models import (
    AnalysisReportV2,
    AuditEvent,
    EvidenceItem,
    ExtractedFact,
    PolicyDecision,
)


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'ORG-DEFAULT',
    source_text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    page_number INTEGER NOT NULL DEFAULT 1,
    clause_reference TEXT,
    matched_terms TEXT DEFAULT '[]',
    extraction_method TEXT DEFAULT 'regex',
    extractor_confidence REAL DEFAULT 0.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extracted_facts (
    fact_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'ORG-DEFAULT',
    evidence_id TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'definitive',
    inconclusive_reason TEXT,
    extractor_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(evidence_id) REFERENCES evidence_items(evidence_id)
);

CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'ORG-DEFAULT',
    policy_id TEXT NOT NULL,
    decision_outcome TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    confidence REAL DEFAULT 0.0,
    facts_used TEXT DEFAULT '[]',
    evidence_ids TEXT DEFAULT '[]',
    explanation TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    statute_ref TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses_v2 (
    report_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'ORG-DEFAULT',
    buyer_name TEXT NOT NULL,
    document_id TEXT NOT NULL,
    compliance_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    recovery_stage TEXT NOT NULL,
    report_json TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL DEFAULT 'analysis',
    changes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyses_tenant ON analyses_v2(tenant_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses_v2(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_events(org_id);
"""


class VasooliRepository:
    """
    Durable persistence layer for Vasooli domain entities with transaction safety.
    """

    def __init__(self, db_path: str = "vasooli_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for table in ["evidence_items", "extracted_facts", "policy_decisions", "analyses_v2"]:
                if table in tables:
                    cols = [c[1] for c in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
                    if "tenant_id" not in cols:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'ORG-DEFAULT'")
            conn.commit()
            conn.executescript(SQLITE_SCHEMA)
        finally:
            conn.close()

    def report_exists(self, report_id: str, tenant_id: str = "ORG-DEFAULT") -> bool:
        """Checks if a report_id already exists in the database."""
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT 1 FROM analyses_v2 WHERE report_id = ? AND tenant_id = ?",
                (report_id, tenant_id),
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    def save_analysis_report(
        self,
        report: AnalysisReportV2,
        tenant_id: str = "ORG-DEFAULT",
        allow_overwrite: bool = False,
    ) -> None:
        """
        Saves a complete AnalysisReportV2 and its constituent entities in an atomic transaction.
        Rolls back automatically on any error.
        """
        conn = self._get_conn()
        try:
            conn.execute("BEGIN TRANSACTION")

            if not allow_overwrite and self.report_exists(report.report_id, tenant_id):
                raise DuplicateReportError(f"Report ID '{report.report_id}' already exists.")

            # 1. Save Facts & Evidence
            for f in report.extracted_facts:
                ev = f.evidence
                conn.execute(
                    """
                    INSERT OR REPLACE INTO evidence_items 
                    (evidence_id, document_id, tenant_id, source_text, start_char, end_char, page_number, clause_reference, matched_terms, extraction_method, extractor_confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ev.evidence_id,
                        ev.source_document_id,
                        tenant_id,
                        ev.source_text,
                        ev.start_char,
                        ev.end_char,
                        ev.page_number,
                        ev.clause_reference,
                        json.dumps(ev.matched_terms),
                        ev.extraction_method,
                        ev.extractor_confidence,
                        ev.created_at.isoformat(),
                    ),
                )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO extracted_facts 
                    (fact_id, document_id, tenant_id, evidence_id, fact_type, fact_value, confidence, status, inconclusive_reason, extractor_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f.fact_id,
                        report.document_id,
                        tenant_id,
                        f.evidence.evidence_id,
                        f.fact_type.value,
                        json.dumps(f.value, default=str),
                        f.confidence,
                        f.status.value,
                        f.inconclusive_reason,
                        f.extractor_version,
                        f.created_at.isoformat(),
                    ),
                )

            # 2. Save Decisions
            for d in report.policy_decisions:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO policy_decisions 
                    (decision_id, document_id, tenant_id, policy_id, decision_outcome, severity, confidence, facts_used, evidence_ids, explanation, policy_version, statute_ref, review_status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.decision_id,
                        report.document_id,
                        tenant_id,
                        d.policy_id,
                        d.decision.value,
                        d.severity.value,
                        d.confidence,
                        json.dumps(d.facts_used),
                        json.dumps(d.evidence_ids),
                        d.explanation,
                        d.policy_version,
                        d.statute_ref,
                        d.review_status,
                        d.created_at.isoformat(),
                    ),
                )

            # 3. Save Main Analysis Report
            conn.execute(
                """
                INSERT OR REPLACE INTO analyses_v2 
                (report_id, tenant_id, buyer_name, document_id, compliance_score, risk_level, recovery_stage, report_json, pipeline_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.report_id,
                    tenant_id,
                    report.buyer_name,
                    report.document_id,
                    report.scorecard.final_score,
                    report.scorecard.risk_level,
                    report.scorecard.recovery_stage.value,
                    report.json(),
                    report.build_metadata.version,
                    report.analyzed_at.isoformat(),
                ),
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            if isinstance(e, DuplicateReportError):
                raise
            raise PersistenceError(f"Transaction failed while saving report {report.report_id}: {str(e)}") from e
        finally:
            conn.close()

    def save_with_audit(
        self,
        report: AnalysisReportV2,
        audit_event: AuditEvent,
        tenant_id: str = "ORG-DEFAULT",
    ) -> None:
        """
        Atomically saves an analysis report and an audit event in the same transaction.
        """
        conn = self._get_conn()
        try:
            conn.execute("BEGIN TRANSACTION")

            # 1. Insert audit event
            conn.execute(
                """
                INSERT INTO audit_events
                (event_id, org_id, actor_id, event_type, resource_id, resource_type, changes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_event.event_id,
                    audit_event.org_id,
                    audit_event.actor_id,
                    audit_event.event_type,
                    audit_event.resource_id,
                    audit_event.resource_type,
                    json.dumps(audit_event.changes, default=str),
                    audit_event.created_at.isoformat(),
                ),
            )

            # 2. Save Analysis Report
            conn.execute(
                """
                INSERT INTO analyses_v2 
                (report_id, tenant_id, buyer_name, document_id, compliance_score, risk_level, recovery_stage, report_json, pipeline_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.report_id,
                    tenant_id,
                    report.buyer_name,
                    report.document_id,
                    report.scorecard.final_score,
                    report.scorecard.risk_level,
                    report.scorecard.recovery_stage.value,
                    report.json(),
                    report.build_metadata.version,
                    report.analyzed_at.isoformat(),
                ),
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise PersistenceError(f"Atomic save_with_audit failed: {str(e)}") from e
        finally:
            conn.close()

    def get_analysis_report(self, report_id: str, tenant_id: str = "ORG-DEFAULT") -> Optional[AnalysisReportV2]:
        """Retrieves an AnalysisReportV2 by report_id and tenant_id."""
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT report_json FROM analyses_v2 WHERE report_id = ? AND tenant_id = ?",
                (report_id, tenant_id),
            )
            row = cur.fetchone()
            if row:
                return AnalysisReportV2.parse_raw(row["report_json"])
            return None
        finally:
            conn.close()

    def list_analysis_reports(self, tenant_id: str = "ORG-DEFAULT", limit: int = 50) -> List[Dict[str, Any]]:
        """Lists metadata for all analysis reports filtered by tenant."""
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """
                SELECT report_id, tenant_id, buyer_name, document_id, compliance_score, risk_level, recovery_stage, pipeline_version, created_at
                FROM analyses_v2 
                WHERE tenant_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (tenant_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
