"""End-to-end, read-only preflight for a Bravo migration batch.

The preflight validates the envelope, checks that prepared candidates match its
source inventory exactly, then delegates to the pure dry-run planner. It has no
database, filesystem, network, or mutation capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_envelope import (
    EnvelopeIssue,
    EnvelopeValidation,
    validate_batch_envelope,
)
from app.core.migration_identity import SourceIdentity
from app.core.migration_plan import (
    DryRunCandidate,
    DryRunPlan,
    build_dry_run_plan,
)


@dataclass(frozen=True, slots=True)
class PreflightResult:
    valid: bool
    envelope_validation: EnvelopeValidation
    issues: tuple[EnvelopeIssue, ...]
    plan: DryRunPlan | None


def run_migration_preflight(
    envelope: Any,
    candidates: tuple[DryRunCandidate, ...],
    *,
    already_known_sources: frozenset[SourceIdentity] = frozenset(),
) -> PreflightResult:
    """Validate one in-memory batch and produce a plan only if it is coherent."""
    validation = validate_batch_envelope(envelope)
    issues = list(validation.issues)

    if not validation.valid:
        return PreflightResult(False, validation, tuple(issues), None)

    # The validator has established these mappings and shapes.
    source_system = envelope["sourceSystem"]
    collections: Mapping[str, list[Mapping[str, Any]]] = envelope["collections"]
    presence: Mapping[str, bool] = envelope["collectionPresence"]

    expected: set[SourceIdentity] = set()
    for collection_name, records in collections.items():
        if presence[collection_name] is False and records:
            issues.append(
                EnvelopeIssue(
                    "absent_collection_has_records",
                    f"collections.{collection_name}",
                    "Coleção marcada como ausente não pode conter registros.",
                )
            )
        for record in records:
            expected.add(
                SourceIdentity(
                    source_system=source_system,
                    source_collection=collection_name,
                    legacy_id=record["id"],
                )
            )

    supplied_list = [candidate.identity for candidate in candidates]
    supplied = set(supplied_list)

    if len(supplied_list) != len(supplied):
        issues.append(
            EnvelopeIssue(
                "duplicate_candidate_identity",
                "candidates",
                "Há identidades de origem repetidas entre os candidatos preparados.",
            )
        )

    for identity in supplied:
        if identity.source_system != source_system:
            issues.append(
                EnvelopeIssue(
                    "candidate_source_system_mismatch",
                    "candidates",
                    "O sistema de origem do candidato difere do envelope.",
                )
            )

    missing_candidates = expected - supplied
    unexpected_candidates = supplied - expected
    if missing_candidates:
        issues.append(
            EnvelopeIssue(
                "candidate_inventory_incomplete",
                "candidates",
                f"Faltam candidatos para {len(missing_candidates)} registro(s) do envelope.",
            )
        )
    if unexpected_candidates:
        issues.append(
            EnvelopeIssue(
                "candidate_not_in_envelope",
                "candidates",
                f"Existem {len(unexpected_candidates)} candidato(s) fora do inventário do envelope.",
            )
        )

    if issues:
        return PreflightResult(False, validation, tuple(issues), None)

    plan = build_dry_run_plan(
        candidates,
        already_known_sources=already_known_sources,
    )
    return PreflightResult(True, validation, (), plan)
