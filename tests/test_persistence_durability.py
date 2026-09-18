"""
Tests for Persistence Durability, Transaction Safety, and Audit Immutability.
"""

import os
import pytest
from datetime import datetime
from vasooli.domain.enums import RecoveryStage, ReviewRouting
from vasooli.domain.errors import AuditIntegrityError, DuplicateReportError
from vasooli.domain.models import (
    AnalysisReportV2,
    AuditEvent,
    BuildMetadata,
    ComplianceScorecard,
    ReviewDecision,
)
from vasooli.persistence.audit import AuditTrailManager
from vasooli.persistence.repository import VasooliRepository


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_durability.db")
    return db_file


def _create_dummy_report(report_id: str, tenant_id: str = "ORG-DEFAULT") -> AnalysisReportV2:
    return AnalysisReportV2(
        report_id=report_id,
        report_version=1,
        document_id=f"DOC-{report_id}",
        buyer_name="Acme Corp",
        extracted_facts=[],
        policy_decisions=[],
        scorecard=ComplianceScorecard(
            base_score=100,
            final_score=100,
            risk_level="low",
            recovery_stage=RecoveryStage.PREVENTIVE_REVISE,
        ),
        review_decision=ReviewDecision(
            needs_human_review=False,
            confidence_score=0.98,
            auto_approved=True,
            recommended_action=ReviewRouting.AUTO_APPROVE,
        ),
        build_metadata=BuildMetadata(version="2.0.0"),
    )


def test_duplicate_report_id_blocked(temp_db):
    repo = VasooliRepository(db_path=temp_db)
    report = _create_dummy_report("REP-DUP-001")

    # First save succeeds
    repo.save_analysis_report(report)

    # Second save with same ID raises DuplicateReportError
    with pytest.raises(DuplicateReportError):
        repo.save_analysis_report(report, allow_overwrite=False)


def test_data_persists_across_reconnect(temp_db):
    repo1 = VasooliRepository(db_path=temp_db)
    report = _create_dummy_report("REP-PERSIST-001")
    repo1.save_analysis_report(report)

    # Open fresh repository connection on same DB file
    repo2 = VasooliRepository(db_path=temp_db)
    fetched = repo2.get_analysis_report("REP-PERSIST-001")
    assert fetched is not None
    assert fetched.report_id == "REP-PERSIST-001"
    assert fetched.buyer_name == "Acme Corp"


def test_tenant_isolation(temp_db):
    repo = VasooliRepository(db_path=temp_db)
    report = _create_dummy_report("REP-TENANT-001")

    repo.save_analysis_report(report, tenant_id="TENANT-ALPHA")

    # Query from different tenant should return None
    assert repo.get_analysis_report("REP-TENANT-001", tenant_id="TENANT-BETA") is None
    # Query from correct tenant returns report
    assert repo.get_analysis_report("REP-TENANT-001", tenant_id="TENANT-ALPHA") is not None


def test_audit_event_hash_chain_and_tamper_detection(temp_db):
    audit_mgr = AuditTrailManager(org_id="ORG-TEST", db_path=temp_db)

    audit_mgr.record_event("analysis_created", "user_1", "REP-01", {"status": "created"})
    audit_mgr.record_event("review_submitted", "user_2", "REP-01", {"status": "approved"})

    assert audit_mgr.verify_integrity() is True

    # Reload from disk into fresh manager
    audit_mgr_reloaded = AuditTrailManager(org_id="ORG-TEST", db_path=temp_db)
    assert len(audit_mgr_reloaded.get_events()) == 2
    assert audit_mgr_reloaded.verify_integrity() is True

    # Tamper with an in-memory event payload
    events = audit_mgr_reloaded.get_events()
    events[0].changes["tampered_key"] = "hacked"
    with pytest.raises(AuditIntegrityError):
        audit_mgr_reloaded.verify_integrity()
