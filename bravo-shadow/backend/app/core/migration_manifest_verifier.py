"""Cross-check a migration manifest against its in-memory batch evidence.

This verifier is pure and read-only. It neither authorizes nor executes imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import PreflightResult
from app.core.migration_report import PreflightReport, build_preflight_report
from app.core.migration_manifest import (
    MigrationManifest,
    build_migration_manifest,
    verify_migration_manifest,
)


@dataclass(frozen=True, slots=True)
class ManifestIntegrityIssue:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ManifestIntegrityResult:
    valid: bool
    issues: tuple[ManifestIntegrityIssue, ...]


def verify_manifest_against_batch(
    manifest: MigrationManifest,
    envelope: Mapping[str, Any],
    candidates: tuple[DryRunCandidate, ...],
    preflight: PreflightResult,
    report: PreflightReport,
) -> ManifestIntegrityResult:
    """Verify hash, envelope identity, report, candidates, and deterministic rebuild."""
    issues: list[ManifestIntegrityIssue] = []

    def add(code: str, message: str) -> None:
        issues.append(ManifestIntegrityIssue(code, message))

    if not verify_migration_manifest(manifest):
        add("manifest_hash_mismatch", "O conteúdo do manifesto não corresponde ao hash registrado.")

    try:
        expected_report = build_preflight_report(envelope, candidates, preflight)
    except (KeyError, TypeError, ValueError, AttributeError):
        add("report_rebuild_failed", "Não foi possível reconstruir o relatório a partir das evidências.")
        expected_report = None

    if expected_report is not None and expected_report != report:
        add("report_evidence_mismatch", "O relatório apresentado difere do relatório reconstruído.")

    if not preflight.valid or preflight.plan is None:
        add("preflight_not_valid", "O pré-flight não está válido ou não contém plano.")
    elif len(preflight.plan.records) != len(candidates):
        add("plan_candidate_count_mismatch", "A quantidade de decisões difere da quantidade de candidatos.")
    else:
        for candidate, planned in zip(candidates, preflight.plan.records):
            if candidate.identity != planned.identity:
                add("plan_candidate_identity_mismatch", "A ordem ou identidade dos candidatos difere do plano.")
                break

    try:
        expected_manifest = build_migration_manifest(
            envelope,
            candidates,
            preflight,
            expected_report if expected_report is not None else report,
            environment=manifest.environment,
            importer_version=manifest.importer_version,
            mapping_version=manifest.mapping_version,
            created_at=manifest.created_at,
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        expected_manifest = None
        add("manifest_rebuild_failed", "Não foi possível reconstruir o manifesto a partir do lote.")

    if expected_manifest is not None and expected_manifest != manifest:
        add("manifest_evidence_mismatch", "O manifesto não corresponde ao envelope, plano e versões informados.")

    return ManifestIntegrityResult(valid=not issues, issues=tuple(issues))
