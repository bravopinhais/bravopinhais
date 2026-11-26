from dataclasses import replace

from app.core.migration_review import append_review, verify_review_ledger
from app.core.migration_review_flow import build_review_workspace
from app.core.migration_manifest import build_migration_manifest
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report
from test_migration_decisions import setup_batch


def batch_evidence():
    envelope, candidates, preflight, manifest = setup_batch()
    report = build_preflight_report(envelope, candidates, preflight)
    return envelope, candidates, preflight, report, manifest


def test_workspace_integrates_verified_manifest_queue_and_empty_ledger():
    envelope, candidates, preflight, report, manifest = batch_evidence()

    workspace = build_review_workspace(
        manifest, envelope, candidates, preflight, report
    )

    assert workspace.valid is True
    assert workspace.batch_id == manifest.batch_id
    assert workspace.manifest_hash == manifest.manifest_hash
    assert workspace.integrity_issue_codes == ()
    assert workspace.register is not None
    assert workspace.ledger is not None
    assert workspace.register.pending_count == 3
    assert workspace.ledger.events == ()
    assert workspace.register.automatic_resolution_count == 0


def test_workspace_accepts_review_and_retains_it_without_executing_import():
    envelope, candidates, preflight, report, manifest = batch_evidence()
    workspace = build_review_workspace(
        manifest, envelope, candidates, preflight, report
    )
    assert workspace.register is not None and workspace.ledger is not None
    decision_id = workspace.register.pending[0].decision_id

    reviewed = append_review(
        workspace.ledger,
        workspace.register,
        event_id="workspace-review-001",
        decision_id=decision_id,
        expected_version=0,
        reviewer_id="human-reviewer",
        choice="keep_blocked",
        rationale="Manter bloqueado até validação da origem.",
        reviewed_at="2026-11-26T16:00:00-03:00",
    )

    assert verify_review_ledger(reviewed, workspace.register) is True
    assert workspace.ledger.events == ()
    assert len(reviewed.events) == 1
    assert reviewed.events[0].choice == "keep_blocked"


def test_workspace_fails_closed_when_manifest_or_evidence_is_tampered():
    envelope, candidates, preflight, report, manifest = batch_evidence()
    tampered_manifest = replace(manifest, environment="production")

    workspace = build_review_workspace(
        tampered_manifest, envelope, candidates, preflight, report
    )

    assert workspace.valid is False
    assert workspace.register is None
    assert workspace.ledger is None
    assert "manifest_hash_mismatch" in workspace.integrity_issue_codes


def test_workspace_fails_closed_when_report_does_not_match_evidence():
    envelope, candidates, preflight, report, manifest = batch_evidence()
    altered_report = replace(report, ready=report.ready + 1)

    workspace = build_review_workspace(
        manifest, envelope, candidates, preflight, altered_report
    )

    assert workspace.valid is False
    assert workspace.register is None
    assert workspace.ledger is None
    assert "report_evidence_mismatch" in workspace.integrity_issue_codes

def test_workspace_fails_closed_if_derived_decision_register_is_inconsistent(monkeypatch):
    import app.core.migration_review_flow as review_flow

    envelope, candidates, preflight, report, manifest = batch_evidence()
    original_builder = review_flow.build_decision_register

    def tampered_builder(current_manifest, current_preflight):
        register = original_builder(current_manifest, current_preflight)
        return replace(register, ready_count=register.ready_count + 1)

    monkeypatch.setattr(review_flow, "build_decision_register", tampered_builder)

    workspace = build_review_workspace(
        manifest, envelope, candidates, preflight, report
    )

    assert workspace.valid is False
    assert workspace.register is None
    assert workspace.ledger is None
    assert "decision_register_evidence_mismatch" in workspace.integrity_issue_codes
