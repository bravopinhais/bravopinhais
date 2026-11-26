from dataclasses import replace

import pytest

from app.core.migration_batch_state import (
    BatchApproval,
    BatchState,
    BatchTransitionError,
    transition_batch,
)


HASH = "a" * 64


def prepared(**changes):
    return replace(
        BatchState(
            batch_id="batch-synthetic-001",
            manifest_hash=HASH,
            environment="ci_ephemeral",
        ),
        **changes,
    )


def approve(state=None, *, manifest_hash=HASH):
    return transition_batch(
        state or prepared(),
        "approved",
        approval=BatchApproval(
            reviewer_id="reviewer@example.test",
            approved_at="2026-11-26T18:00:00-03:00",
            manifest_hash=manifest_hash,
        ),
    )


def test_valid_flow_requires_approval_and_exact_dry_run_hash():
    state = approve()
    assert state.status == "approved"
    applying = transition_batch(
        state, "applying", expected_manifest_hash=HASH
    )
    applied = transition_batch(applying, "applied")
    verified = transition_batch(applied, "verified")

    assert [state.status, applying.status, applied.status, verified.status] == [
        "approved", "applying", "applied", "verified"
    ]


def test_approval_is_bound_to_exact_manifest_hash():
    with pytest.raises(BatchTransitionError, match="approval_manifest_mismatch"):
        approve(manifest_hash="b" * 64)


def test_apply_requires_approved_manifest_and_exact_dry_run():
    approved = approve()
    with pytest.raises(BatchTransitionError, match="dry_run_manifest_mismatch"):
        transition_batch(approved, "applying", expected_manifest_hash="b" * 64)
    with pytest.raises(BatchTransitionError, match="approved_batch_required"):
        transition_batch(prepared(), "applying", expected_manifest_hash=HASH)


@pytest.mark.parametrize("environment", ["production", "staging", "shadow", ""])
def test_non_disposable_environments_are_rejected(environment):
    with pytest.raises(BatchTransitionError, match="environment_not_allowed"):
        transition_batch(prepared(environment=environment), "failed")


def test_terminal_states_cannot_be_reopened():
    failed = transition_batch(prepared(), "failed")
    rolled_back = transition_batch(
        transition_batch(
            transition_batch(approve(), "applying", expected_manifest_hash=HASH),
            "applied",
        ),
        "rolled_back",
    )
    for state in (failed, rolled_back):
        with pytest.raises(BatchTransitionError, match="invalid_status_transition"):
            transition_batch(state, "prepared")


def test_rollback_requires_applied_or_verified_state():
    with pytest.raises(BatchTransitionError, match="invalid_status_transition"):
        transition_batch(approve(), "rolled_back")


def test_original_immutable_state_is_not_modified():
    original = prepared()
    approved = approve(original)

    assert original.status == "prepared"
    assert original.approval is None
    assert approved.status == "approved"


def test_failed_apply_can_be_recorded_but_cannot_be_retried_in_same_batch():
    applying = transition_batch(
        approve(), "applying", expected_manifest_hash=HASH
    )
    failed = transition_batch(applying, "failed")

    assert failed.status == "failed"
    with pytest.raises(BatchTransitionError, match="invalid_status_transition"):
        transition_batch(failed, "applying", expected_manifest_hash=HASH)
