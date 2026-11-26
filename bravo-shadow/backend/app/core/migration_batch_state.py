"""Pure, fail-closed state machine for a migration batch.

This module performs no I/O. A PostgreSQL adapter must call these rules while
holding a row lock and persist the returned transition in the same transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BatchStatus = Literal[
    "prepared", "approved", "applying", "applied",
    "verified", "failed", "rolled_back",
]

ALLOWED_ENVIRONMENTS = frozenset({"local_disposable", "ci_ephemeral"})
TRANSITIONS: dict[str, frozenset[str]] = {
    "prepared": frozenset({"approved", "failed"}),
    "approved": frozenset({"applying", "failed"}),
    "applying": frozenset({"applied", "failed"}),
    "applied": frozenset({"verified", "failed", "rolled_back"}),
    "verified": frozenset({"rolled_back"}),
    "failed": frozenset(),
    "rolled_back": frozenset(),
}


class BatchTransitionError(ValueError):
    """Raised when a batch transition violates the migration safety contract."""


@dataclass(frozen=True, slots=True)
class BatchApproval:
    reviewer_id: str
    approved_at: str
    manifest_hash: str


@dataclass(frozen=True, slots=True)
class BatchState:
    batch_id: str
    manifest_hash: str
    environment: str
    status: BatchStatus = "prepared"
    approval: BatchApproval | None = None


def transition_batch(
    state: BatchState,
    target: BatchStatus,
    *,
    approval: BatchApproval | None = None,
    expected_manifest_hash: str | None = None,
) -> BatchState:
    """Validate and return a new state; caller persists atomically under row lock."""
    if not isinstance(state, BatchState):
        raise BatchTransitionError("invalid_batch_state")
    if not state.batch_id.strip() or not state.manifest_hash.strip():
        raise BatchTransitionError("batch_identity_required")
    if state.environment not in ALLOWED_ENVIRONMENTS:
        raise BatchTransitionError("environment_not_allowed")
    if state.status not in TRANSITIONS or target not in TRANSITIONS:
        raise BatchTransitionError("unknown_batch_status")
    if target not in TRANSITIONS[state.status]:
        raise BatchTransitionError("invalid_status_transition")

    if target == "approved":
        if not isinstance(approval, BatchApproval):
            raise BatchTransitionError("approval_required")
        if not approval.reviewer_id.strip() or not approval.approved_at.strip():
            raise BatchTransitionError("approval_identity_and_time_required")
        if approval.manifest_hash != state.manifest_hash:
            raise BatchTransitionError("approval_manifest_mismatch")
        return BatchState(
            batch_id=state.batch_id,
            manifest_hash=state.manifest_hash,
            environment=state.environment,
            status="approved",
            approval=approval,
        )

    if target == "applying":
        if state.approval is None:
            raise BatchTransitionError("approved_batch_required")
        if state.approval.manifest_hash != state.manifest_hash:
            raise BatchTransitionError("approval_manifest_mismatch")
        if expected_manifest_hash != state.manifest_hash:
            raise BatchTransitionError("dry_run_manifest_mismatch")

    if target in {"applied", "verified", "rolled_back"} and state.approval is None:
        raise BatchTransitionError("approved_batch_required")

    return BatchState(
        batch_id=state.batch_id,
        manifest_hash=state.manifest_hash,
        environment=state.environment,
        status=target,
        approval=state.approval,
    )
