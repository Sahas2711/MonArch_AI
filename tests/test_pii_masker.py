"""
Tests for PII Masker and Evidence Offset Preservation.
"""

from vasooli.security.pii_masker import PIIMasker, MaskReplacement


def test_pan_masking():
    masker = PIIMasker()
    text = "Supplier Ramesh Kumar, PAN ABCDE1234F, agrees to payment terms."
    res = masker.mask(text)
    assert "[PAN_REDACTED]" in res.sanitized_text
    assert "ABCDE1234F" not in res.sanitized_text
    assert len(res.mask_map) == 1
    assert res.mask_map[0].original == "ABCDE1234F"
    assert res.mask_map[0].pii_type == "pan"


def test_aadhaar_and_gstin_masking():
    masker = PIIMasker()
    text = "GSTIN: 27ABCDE1234F1Z5 and Aadhaar: 2345 6789 0123 on record."
    res = masker.mask(text)
    assert "[GSTIN_REDACTED]" in res.sanitized_text
    assert "[AADHAAR_REDACTED]" in res.sanitized_text
    assert len(res.mask_map) == 2


def test_unmask_roundtrip():
    masker = PIIMasker()
    orig = "Contact john.doe@example.com or call +91 9876543210 with PAN ABCDE1234F."
    res = masker.mask(orig)
    assert "[EMAIL_REDACTED]" in res.sanitized_text
    assert "[PHONE_REDACTED]" in res.sanitized_text
    assert "[PAN_REDACTED]" in res.sanitized_text

    unmasked = masker.unmask(res.sanitized_text, res.mask_map)
    assert unmasked == orig


def test_offset_preservation():
    masker = PIIMasker()
    text = "Invoice for PAN ABCDE1234F due in 30 days."
    res = masker.mask(text)
    rep = res.mask_map[0]
    # Check that start_char and end_char accurately index into original_text
    assert res.original_text[rep.start_char:rep.end_char] == "ABCDE1234F"
