"""Read persisted apply authorization under locks on a caller-owned transaction.

The caller must keep this same transaction open through business, provenance,
state-transition and audit writes. This module never opens or commits a
connection and is not wired to routes or the application composition root.
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


def _stored_text(value: Any) -> str | None:
    # Do not turn SQL NULL, numbers, or malformed driver values into strings:
    # str(None) would otherwise become the non-empty identity "None".
    return value if isinstance(value, str) and value.strip() else None


def _timestamp(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return value if isinstance(value, str) and value.strip() else None


def load_locked_apply_authorization(
    connection: Any,
    *,
    batch_id: str,
    execution_id: str,
    manifest_sha256: str,
    plan_sha256: str,
    source_system: str,
) -> LockedApplyAuthorization:
    """Lock and validate batch -> execution -> approval in a fixed lock order.

    Must run inside a caller-owned transaction with autocommit disabled.
    The caller retains all row locks until its business/provenance/audit writes
    and state transitions commit or roll back together.
    """
    if connection is None or not callable(getattr(connection, "cursor", None)):
        return LockedApplyAuthorization(False, ("transaction_connection_required",))
    if getattr(connection, "autocommit", None) is not False:
        return LockedApplyAuthorization(False, ("autocommit_must_be_disabled",))
    for value in (batch_id, execution_id, manifest_sha256, plan_sha256, source_system):
        if not isinstance(value, str) or not value.strip():
            return LockedApplyAuthorization(False, ("expected_identity_required",))

    batch = _fetchone(
        connection,
        """
        SELECT batch_id, manifest_hash, environment, status, mode,
               source_system, approved_manifest_hash
        FROM bravo_shadow.migration_batches
        WHERE batch_id = %s
        FOR UPDATE
        """,
        (batch_id,),
    )
    if batch is None:
        return LockedApplyAuthorization(False, ("batch_not_found",))
    if not isinstance(batch, (tuple, list)) or len(batch) != 7:
        return LockedApplyAuthorization(False, ("stored_batch_shape_invalid",))
    batch_id_db, manifest_db, environment_db, status_db, mode_db, source_db, approved_manifest_db = batch
    if _stored_text(batch_id_db) != batch_id or _stored_text(manifest_db) != manifest_sha256:
        return LockedApplyAuthorization(False, ("batch_manifest_mismatch",))
    if _stored_text(environment_db) != "local_disposable":
        return LockedApplyAuthorization(False, ("batch_environment_not_allowed",))
    if _stored_text(status_db) != "approved":
        return LockedApplyAuthorization(False, ("batch_not_approved",))
    if _stored_text(mode_db) != "apply":
        return LockedApplyAuthorization(False, ("batch_mode_not_apply",))
    if _stored_text(source_db) != source_system:
        return LockedApplyAuthorization(False, ("batch_source_system_mismatch",))
    if _stored_text(approved_manifest_db) != manifest_sha256:
        return LockedApplyAuthorization(False, ("batch_manifest_not_explicitly_approved",))

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
    if not isinstance(execution_row, (tuple, list)) or len(execution_row) != 7:
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
    if not isinstance(approval_row, (tuple, list)) or len(approval_row) != 9:
        return LockedApplyAuthorization(False, ("stored_approval_shape_invalid",))

    execution_values = [_stored_text(value) for value in execution_row]
    approval_values = [_stored_text(value) for value in approval_row[:8]]
    approved_at = _timestamp(approval_row[8])
    if any(value is None for value in execution_values + approval_values) or approved_at is None:
        return LockedApplyAuthorization(False, ("stored_authorization_record_invalid",))

    execution = MigrationExecution(
        execution_id=execution_values[0],
        batch_id=execution_values[1],
        manifest_sha256=execution_values[2],
        plan_sha256=execution_values[3],
        environment=execution_values[4],
        requested_by_subject=execution_values[5],
        status=execution_values[6],
    )
    approval = MigrationApplyApproval(
        approval_id=approval_values[0],
        execution_id=approval_values[1],
        batch_id=approval_values[2],
        manifest_sha256=approval_values[3],
        plan_sha256=approval_values[4],
        decision=approval_values[5],
        reviewer_subject=approval_values[6],
        rationale=approval_values[7],
        approved_at=approved_at,
    )

    if execution.manifest_sha256 != manifest_db:
        return LockedApplyAuthorization(False, ("execution_batch_manifest_mismatch",))
    if execution.environment != environment_db:
        return LockedApplyAuthorization(False, ("execution_batch_environment_mismatch",))

    result: ApplyAuthorizationResult = verify_apply_authorization(
        execution,
        approval,
        expected_batch_id=batch_id,
        expected_execution_id=execution_id,
        expected_manifest_sha256=manifest_sha256,
        expected_plan_sha256=plan_sha256,
    )
    return LockedApplyAuthorization(result.authorized, result.issues, execution, approval)
