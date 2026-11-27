"""Synthetic tests for exact-plan apply approval; no persistence or DB access."""
from dataclasses import replace

from app.core.migration_apply_authorization import (
    MigrationApplyApproval,
    MigrationExecution,
    verify_apply_authorization,
)

H = "a" * 64
P = "b" * 64


def records():
    execution = MigrationExecution(
        "exec-1", "batch-1", H, P, "local_disposable", "google-sub-requester", "approved"
    )
    approval = MigrationApplyApproval(
        "approval-1", "exec-1", "batch-1", H, P, "approved",
        "google-sub-reviewer", "Plano revisado", "2026-11-27T17:00:00-03:00"
    )
    return execution, approval


def verify(execution, approval):
    return verify_apply_authorization(
        execution, approval, expected_batch_id="batch-1",
        expected_execution_id="exec-1", expected_manifest_sha256=H,
        expected_plan_sha256=P,
    )


def test_exact_execution_and_independent_approval_are_authorized():
    execution, approval = records()
    result = verify(execution, approval)
    assert result.authorized is True
    assert result.issues == ()


def test_reviewer_must_differ_from_requester():
    execution, approval = records()
    result = verify(execution, replace(approval, reviewer_subject=execution.requested_by_subject))
    assert "requester_and_reviewer_must_differ" in result.issues


def test_environment_and_execution_state_fail_closed():
    execution, approval = records()
    assert "apply_environment_not_allowed" in verify(replace(execution, environment="ci_ephemeral"), approval).issues
    assert "execution_not_approved" in verify(replace(execution, status="failed"), approval).issues


def test_rejected_or_mismatched_plan_cannot_authorize():
    execution, approval = records()
    assert "apply_approval_not_approved" in verify(execution, replace(approval, decision="rejected")).issues
    assert "approval_plan_mismatch" in verify(execution, replace(approval, plan_sha256="c" * 64)).issues


def test_naive_timestamp_is_rejected():
    execution, approval = records()
    result = verify(execution, replace(approval, approved_at="2026-11-27T17:00:00"))
    assert "approval_timezone_required" in result.issues


def test_wrong_expected_execution_identity_is_rejected():
    execution, approval = records()
    result = verify_apply_authorization(
        execution, approval, expected_batch_id="batch-1",
        expected_execution_id="exec-other", expected_manifest_sha256=H,
        expected_plan_sha256=P,
    )
    assert "expected_execution_mismatch" in result.issues
