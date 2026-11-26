from dataclasses import replace

from app.core.migration_decision_verifier import verify_decision_register_against_batch
from app.core.migration_decisions import build_decision_register
from app.core.migration_report import build_preflight_report
from test_migration_decisions import setup_batch


def test_decision_register_matches_manifest_preflight_and_report():
    envelope, candidates, preflight, manifest = setup_batch()
    report = build_preflight_report(envelope, candidates, preflight)
    register = build_decision_register(manifest, preflight)

    result = verify_decision_register_against_batch(
        register, manifest, envelope, candidates, preflight, report
    )

    assert result.valid is True
    assert result.issues == ()


def test_decision_register_tampering_is_detected():
    envelope, candidates, preflight, manifest = setup_batch()
    report = build_preflight_report(envelope, candidates, preflight)
    register = build_decision_register(manifest, preflight)
    changed = replace(register, ready_count=register.ready_count + 1)

    result = verify_decision_register_against_batch(
        changed, manifest, envelope, candidates, preflight, report
    )

    assert result.valid is False
    assert "decision_register_evidence_mismatch" in {issue.code for issue in result.issues}


def test_review_register_is_rejected_when_report_evidence_is_tampered():
    envelope, candidates, preflight, manifest = setup_batch()
    report = build_preflight_report(envelope, candidates, preflight)
    changed_report = replace(report, ready=report.ready + 1)
    register = build_decision_register(manifest, preflight)

    result = verify_decision_register_against_batch(
        register, manifest, envelope, candidates, preflight, changed_report
    )

    assert result.valid is False
    assert "migration_evidence_invalid" in {issue.code for issue in result.issues}


def test_review_register_is_rejected_when_manifest_is_tampered():
    envelope, candidates, preflight, manifest = setup_batch()
    report = build_preflight_report(envelope, candidates, preflight)
    register = build_decision_register(manifest, preflight)
    changed_manifest = replace(manifest, importer_version="tampered")

    result = verify_decision_register_against_batch(
        register, changed_manifest, envelope, candidates, preflight, report
    )

    assert result.valid is False
    assert "migration_evidence_invalid" in {issue.code for issue in result.issues}
