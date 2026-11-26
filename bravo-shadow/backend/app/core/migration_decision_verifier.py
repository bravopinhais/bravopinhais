"""Cross-check the human-review register against its migration evidence.

This verifier is pure and read-only. It does not approve decisions or execute imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_decisions import DecisionRegister, build_decision_register
from app.core.migration_manifest import MigrationManifest
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import PreflightResult
from app.core.migration_report import PreflightReport
from app.core.migration_manifest_verifier import verify_manifest_against_batch


@dataclass(frozen=True, slots=True)
class DecisionRegisterIntegrityIssue:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DecisionRegisterIntegrityResult:
    valid: bool
    issues: tuple[DecisionRegisterIntegrityIssue, ...]


def verify_decision_register_against_batch(
    register: DecisionRegister,
    manifest: MigrationManifest,
    envelope: Mapping[str, Any],
    candidates: tuple[DryRunCandidate, ...],
    preflight: PreflightResult,
    report: PreflightReport,
) -> DecisionRegisterIntegrityResult:
    """Require a valid evidence chain and exact deterministic decision register."""
    issues: list[DecisionRegisterIntegrityIssue] = []

    manifest_result = verify_manifest_against_batch(
        manifest, envelope, candidates, preflight, report
    )
    if not manifest_result.valid:
        issues.append(
            DecisionRegisterIntegrityIssue(
                "migration_evidence_invalid",
                "O manifesto, pré-flight ou relatório não passou na verificação de integridade.",
            )
        )

    expected = build_decision_register(manifest, preflight)
    if register != expected:
        issues.append(
            DecisionRegisterIntegrityIssue(
                "decision_register_evidence_mismatch",
                "O registro de decisões difere da fila reconstruída a partir das evidências.",
            )
        )

    return DecisionRegisterIntegrityResult(valid=not issues, issues=tuple(issues))
