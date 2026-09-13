"""
Tests for MSME Clause Extraction Module.
"""

import pytest
from pipeline.extractor import ClauseExtractor, ExtractedClause


@pytest.fixture
def extractor():
    return ClauseExtractor()


def test_extract_payment_days_numeric(extractor):
    text = "Payment shall be released by the Buyer within 90 days from receipt of goods."
    clauses = extractor.extract_from_text(text)
    assert len(clauses) >= 1
    payment_clause = next((c for c in clauses if c.clause_type == "payment_terms"), None)
    assert payment_clause is not None
    assert payment_clause.payment_days == 90
    assert payment_clause.confidence >= 0.85


def test_extract_payment_days_words(extractor):
    text = "Disbursement timeline: All payments shall be made within ninety days following QA."
    clauses = extractor.extract_from_text(text)
    payment_clause = next((c for c in clauses if c.clause_type == "payment_terms"), None)
    assert payment_clause is not None
    assert payment_clause.payment_days == 90


def test_extract_interest_waiver(extractor):
    text = "Payment within 30 days. No interest shall accrue on delayed disbursements under any circumstances."
    clauses = extractor.extract_from_text(text)
    interest_clause = next((c for c in clauses if c.clause_type == "interest_penalty"), None)
    assert interest_clause is not None
    assert interest_clause.has_penalty_interest is False
    assert interest_clause.confidence >= 0.85


def test_extract_compliant_interest(extractor):
    text = "Payment within 45 days. Delayed payments attract 3x RBI bank rate compound interest."
    clauses = extractor.extract_from_text(text)
    interest_clause = next((c for c in clauses if c.clause_type == "interest_penalty"), None)
    assert interest_clause is not None
    assert interest_clause.has_penalty_interest is True


def test_extract_unilateral_cancellation(extractor):
    text = "Buyer reserves the right to cancel the order without notice at any time."
    clauses = extractor.extract_from_text(text)
    cancel_clause = next((c for c in clauses if c.clause_type == "cancellation"), None)
    assert cancel_clause is not None
    assert cancel_clause.has_unilateral_cancellation is True


def test_extract_empty_or_fallback(extractor):
    text = "Standard mutual non-disclosure agreement between the parties."
    clauses = extractor.extract_from_text(text)
    assert len(clauses) >= 1
    assert clauses[0].extraction_method in ["fallback", "regex"]
