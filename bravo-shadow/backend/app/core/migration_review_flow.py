"""Read-only assembly of the pre-migration human-review workspace.

This composes existing evidence verification, the pending-decision register,
and its in-memory review ledger. It cannot import, persist, or alter records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_decisions import DecisionRegister, build_decision_register
from app.core.migration_decision_verifier import verify_decision_register_against_batch
from app.core.migration_manifest import MigrationManifest
from app.core.migration_manifest_verifier import verify_manifest_against_batch
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import PreflightResult
from app.core.migration_report import PreflightReport
from app.core.migration_review import ReviewLedger, create_review_ledger


@dataclass(frozen=True, slots=True)
class ReviewWorkspace:
    valid: bool
    batch_id: str
    manifest_hash: str
    integrity_issue_codes: tuple[str, ...]
    register: DecisionRegister | None
    ledger: ReviewLedger | None


def build_review_workspace(
    manifest: MigrationManifest,
    envelope: Mapping[str, Any],
    candidates: tuple[DryRunCandidate, ...],
    preflight: PreflightResult,
    report: PreflightReport,
) -> ReviewWorkspace:
    """Verify evidence and the derived decision queue before human review."""
    integrity = verify_manifest_against_batch(
        manifest, envelope, candidates, preflight, report
    )
    issue_codes = tuple(issue.code for issue in integrity.issues)
    if not integrity.valid:
        return ReviewWorkspace(
            valid=False,
            batch_id=manifest.batch_id,
            manifest_hash=manifest.manifest_hash,
            integrity_issue_codes=issue_codes,
            register=None,
            ledger=None,
        )

    register = build_decision_register(manifest, preflight)
    register_integrity = verify_decision_register_against_batch(
        register, manifest, envelope, candidates, preflight, report
    )
    if not register_integrity.valid:
        return ReviewWorkspace(
            valid=False,
            batch_id=manifest.batch_id,
            manifest_hash=manifest.manifest_hash,
            integrity_issue_codes=tuple(
                issue.code for issue in register_integrity.issues
            ),
            register=None,
            ledger=None,
        )

    ledger = create_review_ledger(register)
    return ReviewWorkspace(
        valid=True,
        batch_id=manifest.batch_id,
        manifest_hash=manifest.manifest_hash,
        integrity_issue_codes=(),
        register=register,
        ledger=ledger,
    )
