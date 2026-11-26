"""Consolidated, deterministic readiness report for migration evidence.

The report classifies blockers; it does not authorize or execute an import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.migration_pre_import_validation import PreImportValidationReport
from app.core.migration_report import PreflightReport

Severity = Literal["critical", "high", "medium", "low"]


@dataclass(frozen=True, slots=True)
class ReadinessIssue:
    code: str
    severity: Severity
    category: str


@dataclass(frozen=True, slots=True)
class MigrationReadinessReport:
    ready: bool
    preflight_valid: bool
    evidence_valid: bool
    issues: tuple[ReadinessIssue, ...]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


def _classify(code: str) -> ReadinessIssue:
    if code.startswith("export_chain:") or code in {
        "manifest_hash_invalid",
        "snapshot_hash_invalid",
        "snapshot_invalid",
        "source_system_mismatch",
        "source_baseline_mismatch",
        "snapshot_hash_mismatch",
        "record_count_mismatch",
        "export_timestamp_mismatch",
    }:
        return ReadinessIssue(code, "critical", "integrity")
    if code.startswith("reconciliation:") or code in {
        "manifest_not_chain_tip",
        "export_chain_empty",
    }:
        return ReadinessIssue(code, "high", "reconciliation")
    if code in {
        "candidate_inventory_incomplete",
        "candidate_not_in_envelope",
        "duplicate_candidate_identity",
        "candidate_source_system_mismatch",
        "absent_collection_has_records",
    }:
        return ReadinessIssue(code, "high", "inventory")
    if code in {"unsupported_format_version"}:
        return ReadinessIssue(code, "high", "compatibility")
    return ReadinessIssue(code, "medium", "preflight")


def build_migration_readiness_report(
    *,
    preflight: PreflightReport,
    evidence: PreImportValidationReport,
) -> MigrationReadinessReport:
    """Merge preflight and evidence findings into a severity-ranked report."""
    if not isinstance(preflight, PreflightReport):
        raise TypeError("preflight deve ser PreflightReport.")
    if not isinstance(evidence, PreImportValidationReport):
        raise TypeError("evidence deve ser PreImportValidationReport.")

    codes: list[str] = []
    if not preflight.valid and not preflight.issue_codes:
        codes.append("preflight_invalid_without_detail")
    codes.extend(preflight.issue_codes)
    codes.extend(evidence.blockers)

    unique_codes = tuple(dict.fromkeys(codes))
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues = tuple(
        sorted(
            (_classify(code) for code in unique_codes),
            key=lambda issue: (severity_order[issue.severity], issue.category, issue.code),
        )
    )
    counts = {
        severity: sum(issue.severity == severity for issue in issues)
        for severity in severity_order
    }
    return MigrationReadinessReport(
        ready=preflight.valid and evidence.ready and not issues,
        preflight_valid=preflight.valid,
        evidence_valid=evidence.ready,
        issues=issues,
        critical_count=counts["critical"],
        high_count=counts["high"],
        medium_count=counts["medium"],
        low_count=counts["low"],
    )
