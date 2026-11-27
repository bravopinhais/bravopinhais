"""Pure verifier for the persisted apply-execution and approval contract.

This module does not authenticate actors, persist evidence, open connections,
or authorize database writes. Callers must supply records loaded under locks
by a future PostgreSQL adapter and derive actor identities from principals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal

ApplyDecision = Literal["approved", "rejected"]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class MigrationExecution:
    execution_id: str
    batch_id: str
    manifest_sha256: str
    plan_sha256: str
    environment: str
    requested_by_subject: str
    status: str


@dataclass(frozen=True, slots=True)
class MigrationApplyApproval:
    approval_id: str
    execution_id: str
    batch_id: str
    manifest_sha256: str
    plan_sha256: str
    decision: ApplyDecision
    reviewer_subject: str
    rationale: str
    approved_at: str


@dataclass(frozen=True, slots=True)
class ApplyAuthorizationResult:
    authorized: bool
    issues: tuple[str, ...]


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def verify_apply_authorization(
    execution: MigrationExecution,
    approval: MigrationApplyApproval,
    *,
    expected_batch_id: str,
    expected_execution_id: str,
    expected_manifest_sha256: str,
    expected_plan_sha256: str,
) -> ApplyAuthorizationResult:
    """Fail closed unless approval matches the exact persisted execution."""
    issues: list[str] = []
    if not isinstance(execution, MigrationExecution):
        return ApplyAuthorizationResult(False, ("execution_invalid_type",))
    if not isinstance(approval, MigrationApplyApproval):
        return ApplyAuthorizationResult(False, ("approval_invalid_type",))

    for field in (
        execution.execution_id, execution.batch_id, execution.requested_by_subject,
        approval.approval_id, approval.reviewer_subject, approval.rationale,
        approval.execution_id, approval.batch_id,
    ):
        if not _nonempty(field):
            issues.append("required_identity_or_rationale_missing")
            break

    for digest in (
        execution.manifest_sha256, execution.plan_sha256,
        approval.manifest_sha256, approval.plan_sha256,
        expected_manifest_sha256, expected_plan_sha256,
    ):
        if not _sha256(digest):
            issues.append("sha256_format_invalid")
            break

    if execution.environment != "local_disposable":
        issues.append("apply_environment_not_allowed")
    if execution.status != "approved":
        issues.append("execution_not_approved")
    if approval.decision != "approved":
        issues.append("apply_approval_not_approved")
    if approval.execution_id != execution.execution_id:
        issues.append("approval_execution_mismatch")
    if approval.batch_id != execution.batch_id:
        issues.append("approval_batch_mismatch")
    if approval.manifest_sha256 != execution.manifest_sha256:
        issues.append("approval_manifest_mismatch")
    if approval.plan_sha256 != execution.plan_sha256:
        issues.append("approval_plan_mismatch")
    if execution.batch_id != expected_batch_id:
        issues.append("expected_batch_mismatch")
    if execution.execution_id != expected_execution_id:
        issues.append("expected_execution_mismatch")
    if execution.manifest_sha256 != expected_manifest_sha256:
        issues.append("expected_manifest_mismatch")
    if execution.plan_sha256 != expected_plan_sha256:
        issues.append("expected_plan_mismatch")
    if _nonempty(execution.requested_by_subject) and (
        execution.requested_by_subject == approval.reviewer_subject
    ):
        issues.append("requester_and_reviewer_must_differ")

    try:
        timestamp = datetime.fromisoformat(approval.approved_at)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            issues.append("approval_timezone_required")
    except (TypeError, ValueError):
        issues.append("approval_timestamp_invalid")

    return ApplyAuthorizationResult(not issues, tuple(issues))
