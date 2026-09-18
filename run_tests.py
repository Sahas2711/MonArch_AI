"""
Direct Test Runner for Vasooli / MonArch Test Suite.
"""

import sys
import tempfile
import traceback


def run_all():
    passed = 0
    failed = 0

    print("=" * 70)
    print("MONARCH / VASOOLI COMPREHENSIVE PRODUCTION TEST SUITE")
    print("=" * 70)

    # 1. PII Masker Tests
    print("\n[1/6] Running PII Masker & Evidence Offset Tests...")
    import tests.test_pii_masker as t_pii
    for name in ["test_pan_masking", "test_aadhaar_and_gstin_masking", "test_unmask_roundtrip", "test_offset_preservation"]:
        fn = getattr(t_pii, name)
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    # 2. Prompt Injection Tests
    print("\n[2/6] Running Prompt Guard & Multi-Layer Injection Tests...")
    import tests.test_prompt_injection as t_inj
    for name in ["test_direct_injection_keyword_blocked", "test_indirect_instruction_detected", "test_control_character_stripping", "test_suspicious_text_preserved_in_audit", "test_multilingual_injection"]:
        fn = getattr(t_inj, name)
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    # 3. Legal Rules & Cautious Wording Tests
    print("\n[3/6] Running Legal Policy & Cautious Output Wording Tests...")
    import tests.test_legal_rules as t_rules
    for name in ["test_section_15_written_agreement_vs_no_agreement", "test_section_15_delayed_buyer_approval_trigger_is_inconclusive", "test_section_16_below_statutory_rate", "test_contract_act_cautious_wording"]:
        fn = getattr(t_rules, name)
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    # 4. Confidence Gating Tests
    print("\n[4/6] Running Category-Gated Confidence & Ambiguity Gating Tests...")
    import tests.test_confidence_gating as t_conf
    for name in ["test_ambiguous_date_blocks_auto_approval", "test_high_average_with_one_low_category_blocks_auto_approval", "test_clean_compliant_auto_approves"]:
        fn = getattr(t_conf, name)
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    # 5. Persistence Durability Tests
    print("\n[5/6] Running Persistence Durability & Audit Immutability Tests...")
    import tests.test_persistence_durability as t_pers
    with tempfile.TemporaryDirectory() as td:
        db_path = f"{td}/test.db"
        for name in ["test_duplicate_report_id_blocked", "test_data_persists_across_reconnect", "test_tenant_isolation", "test_audit_event_hash_chain_and_tamper_detection"]:
            fn = getattr(t_pers, name)
            try:
                fn(db_path)
                print(f"  [PASS] {name}")
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {name}: {e}")
                traceback.print_exc()
                failed += 1

    # 6. Evaluation Splits & Confusion Matrix Tests
    print("\n[6/6] Running Benchmark Splits & Confusion Matrix Tests...")
    import tests.test_evaluation_splits as t_splits
    for name in ["test_dataset_splits_exist_and_disjoint", "test_confusion_matrix_calculation"]:
        fn = getattr(t_splits, name)
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED (Total: {passed + failed})")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
