"""Verify append-only human review evidence for a pre-import manifest.

This is a pure verifier, not an authentication mechanism, persistence adapter,
approval endpoint, batch transition, or import authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal

from app.core.migration_pre_import_manifest import PreImportManifest

ApprovalDecision = Literal[
    "approved_for_dry_run",
    "rejected",
    "request_changes",
]
_ALLOWED_DECISIONS = frozenset({
    "approved_for_dry_run", "rejected", "request_changes",
})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class PreImportApprovalEvidence:
    event_id: str
    manifest_sha256: str
    raw_source_sha256: str
    snapshot_hash: str
    decision: ApprovalDecision
    reviewer_id: str
    reviewed_at: str
    rationale: str
    sequence_no: int
    scope: str = "dry_run_only"
    writes_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ApprovalEvidenceIssue:
    code: str


@dataclass(frozen=True, slots=True)
class ApprovalEvidenceResult:
    valid: bool
    eligible_for_dry_run: bool
    writes_authorized: bool
    issues: tuple[ApprovalEvidenceIssue, ...]


def verify_pre_import_approval(
    manifest: PreImportManifest,
    evidence: PreImportApprovalEvidence,
) -> ApprovalEvidenceResult:
    """Cross-check review evidence against the exact immutable manifest."""
    issues: list[ApprovalEvidenceIssue] = []

    def add(code: str) -> None:
        issues.append(ApprovalEvidenceIssue(code))

    if not isinstance(evidence, PreImportApprovalEvidence):
        return ApprovalEvidenceResult(
            valid=False,
            eligible_for_dry_run=False,
            writes_authorized=False,
            issues=(ApprovalEvidenceIssue("approval_evidence_invalid_type"),),
        )

    if not isinstance(evidence.event_id, str) or not evidence.event_id.strip():
        add("approval_event_id_required")
    if evidence.manifest_sha256 != manifest.manifest_sha256:
        add("approval_manifest_hash_mismatch")
    if evidence.raw_source_sha256 != manifest.raw_source_sha256:
        add("approval_source_hash_mismatch")
    if evidence.snapshot_hash != manifest.snapshot_hash:
        add("approval_snapshot_hash_mismatch")
    if evidence.decision not in _ALLOWED_DECISIONS:
        add("approval_decision_invalid")
    if not isinstance(evidence.reviewer_id, str) or not evidence.reviewer_id.strip():
        add("approval_reviewer_required")
    if not isinstance(evidence.rationale, str) or not evidence.rationale.strip():
        add("approval_rationale_required")
    if (
        isinstance(evidence.sequence_no, bool)
        or not isinstance(evidence.sequence_no, int)
        or evidence.sequence_no <= 0
    ):
        add("approval_sequence_invalid")
    if evidence.scope != "dry_run_only":
        add("approval_scope_invalid")
    if evidence.writes_authorized is not False:
        add("approval_must_not_authorize_writes")
    if not isinstance(evidence.manifest_sha256, str) or not _SHA256_RE.fullmatch(
        evidence.manifest_sha256
    ):
        add("approval_manifest_hash_invalid")
    if not isinstance(evidence.raw_source_sha256, str) or not _SHA256_RE.fullmatch(
        evidence.raw_source_sha256
    ):
        add("approval_source_hash_invalid")
    if not isinstance(evidence.snapshot_hash, str) or not _SHA256_RE.fullmatch(
        evidence.snapshot_hash
    ):
        add("approval_snapshot_hash_invalid")

    try:
        reviewed_at = datetime.fromisoformat(evidence.reviewed_at)
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
            add("approval_timestamp_timezone_required")
    except (TypeError, ValueError):
        add("approval_timestamp_invalid")

    if evidence.decision == "approved_for_dry_run" and (
        manifest.readiness != "awaiting_human_approval"
        or manifest.pending_gates
        or manifest.integrity_issue_codes
        or manifest.integrity_status != "structurally_clear"
    ):
        add("manifest_not_eligible_for_dry_run")

    valid = not issues
    eligible = valid and evidence.decision == "approved_for_dry_run"
    return ApprovalEvidenceResult(
        valid=valid,
        eligible_for_dry_run=eligible,
        writes_authorized=False,
        issues=tuple(issues),
    )
