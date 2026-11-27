"""Read persisted apply authorization under locks on a caller-owned transaction.

The caller must keep this same transaction open through the eventual business,
provenance and audit writes. This module never opens or commits a connection.
It is not wired to routes or the application composition root.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.migration_apply_authorization import (
    ApplyAuthorizationResult,
    MigrationApplyApproval,
    MigrationExecution,
    verify_apply_authorization,
)


@dataclass(frozen=True, slots=True)
class LockedApplyAuthorization:
    authorized: bool
    issues: tuple[str, ...]
    execution: MigrationExecution | None = None
    approval: MigrationApplyApproval | None = None


def _fetchone(connection: Any, sql: str, params: tuple[Any, ...]) -> Any:
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.fetchone()
    finally:
        cursor.close()


def _timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return "" if value is None else str(value)


def load_locked_apply_authorization(
    connection: Any,
    *,
    batch_id: str,
    execution_id: str,
    manifest_sha256: str,
    plan_sha256: str,
) -> LockedApplyAuthorization:
    """Lock and validate batch -> execution -> approval in a fixed lock order.

    This function deliberately does not commit, rollback, or release locks.
    The caller must execute it inside the same transaction as apply_one_record's
    future integrated unit; calling it as a standalone preflight is unsafe
    because releasing these locks before writes creates a TOCTOU window.
    """
    if connection is None or not callable(getattr(connection, "cursor", None)):
        return LockedApplyAuthorization(False, ("transaction_connection_required",))
    for value in (batch_id, execution_id, manifest_sha256, plan_sha256):
        if not isinstance(value, str) or not value.strip():
            return LockedApplyAuthorization(False, ("expected_identity_required",))

    batch = _fetchone(
        connection,
        """
        SELECT batch_id, manifest_hash, environment, status
        FROM bravo_shadow.migration_batches
        WHERE batch_id = %s
        FOR UPDATE
        """,
        (batch_id,),
    )
    if batch is None:
        return LockedApplyAuthorization(False, ("batch_not_found",))
    if len(batch) != 4:
        return LockedApplyAuthorization(False, ("stored_batch_shape_invalid",))
    if str(batch[0]) != batch_id or str(batch[1]) != manifest_sha256:
        return LockedApplyAuthorization(False, ("batch_manifest_mismatch",))
    if batch[2] != "local_disposable":
        return LockedApplyAuthorization(False, ("batch_environment_not_allowed",))
    if batch[3] != "approved":
        return LockedApplyAuthorization(False, ("batch_not_approved",))

    execution_row = _fetchone(
        connection,
        """
        SELECT execution_id, batch_id, manifest_hash, plan_sha256,
               environment, requested_by_subject, status
        FROM bravo_shadow.migration_executions
        WHERE execution_id = %s AND batch_id = %s
        FOR UPDATE
        """,
        (execution_id, batch_id),
    )
    if execution_row is None:
        return LockedApplyAuthorization(False, ("execution_not_found",))
    if len(execution_row) != 7:
        return LockedApplyAuthorization(False, ("stored_execution_shape_invalid",))

    approval_row = _fetchone(
        connection,
        """
        SELECT approval_id, execution_id, batch_id, manifest_hash, plan_sha256,
               decision, reviewer_subject, rationale, approved_at
        FROM bravo_shadow.migration_apply_approvals
        WHERE execution_id = %s
        FOR UPDATE
        """,
        (execution_id,),
    )
    if approval_row is None:
        return LockedApplyAuthorization(False, ("apply_approval_not_found",))
    if len(approval_row) != 9:
        return LockedApplyAuthorization(False, ("stored_approval_shape_invalid",))

    try:
        execution = MigrationExecution(
            execution_id=str(execution_row[0]),
            batch_id=str(execution_row[1]),
            manifest_sha256=str(execution_row[2]),
            plan_sha256=str(execution_row[3]),
            environment=str(execution_row[4]),
            requested_by_subject=str(execution_row[5]),
            status=str(execution_row[6]),
        )
        approval = MigrationApplyApproval(
            approval_id=str(approval_row[0]),
            execution_id=str(approval_row[1]),
            batch_id=str(approval_row[2]),
            manifest_sha256=str(approval_row[3]),
            plan_sha256=str(approval_row[4]),
            decision=approval_row[5],
            reviewer_subject=str(approval_row[6]),
            rationale=str(approval_row[7]),
            approved_at=_timestamp(approval_row[8]),
        )
    except (TypeError, ValueError):
        return LockedApplyAuthorization(False, ("stored_authorization_record_invalid",))

    if execution.manifest_sha256 != str(batch[1]):
        return LockedApplyAuthorization(False, ("execution_batch_manifest_mismatch",))
    if execution.environment != str(batch[2]):
        return LockedApplyAuthorization(False, ("execution_batch_environment_mismatch",))

    result: ApplyAuthorizationResult = verify_apply_authorization(
        execution,
        approval,
        expected_batch_id=batch_id,
        expected_execution_id=execution_id,
        expected_manifest_sha256=manifest_sha256,
        expected_plan_sha256=plan_sha256,
    )
    return LockedApplyAuthorization(
        result.authorized, result.issues, execution, approval
    )
